#!/usr/bin/env python3
"""
Token-level GFM Classifier model.

Key difference from previous approach: NO mean pooling before classification head.
The classification head receives the FULL sequence of token embeddings
[batch_size, seq_len, hidden_dim].

Two model types:
  1. TokenLevelGFMClassifier — Pre-trained NT-v2 backbone + LoRA fine-tuning
  2. ShallowTransformerClassifier — Single-layer Transformer from scratch
     (MetaTransformer-style ablation with 6-mer tokenizer)

Backbone loading:
  - NT v2 uses AutoModelForMaskedLM → extract .esm as the backbone
  - Handles peft 0.5.0 compatibility for LoRA
"""

import gc
import math
import torch
import torch.nn as nn
from transformers import AutoModelForMaskedLM, AutoTokenizer

from heads import create_head


class TokenLevelGFMClassifier(nn.Module):
    """
    Token-level GFM classifier.
    NO mean pooling — full token sequence → classification head.
    """

    def __init__(
        self,
        backbone_name: str,
        num_classes: int,
        head_type: str = "transformer",
        head_config: dict = None,
        freeze_backbone: bool = False,
        use_lora: bool = True,
        lora_r: int = 16,
        lora_alpha: int = 32,
        lora_dropout: float = 0.05,
        lora_target_modules: list = None,
        gradient_checkpointing: bool = True,
    ):
        super().__init__()

        # ===== 1. Load GFM backbone =====
        print(f"Loading backbone: {backbone_name}")
        full_model = AutoModelForMaskedLM.from_pretrained(
            backbone_name, trust_remote_code=True
        )
        # NT models wrap the base model in .esm
        if hasattr(full_model, "esm"):
            self.backbone = full_model.esm
        else:
            self.backbone = full_model
        self.hidden_dim = self.backbone.config.hidden_size
        print(f"  Hidden dim: {self.hidden_dim}")
        print(f"  Num layers: {self.backbone.config.num_hidden_layers}")

        # Free the LM head
        del full_model
        gc.collect()

        # ===== 2. Gradient checkpointing =====
        if gradient_checkpointing:
            try:
                self.backbone.gradient_checkpointing_enable()
                print("  Gradient checkpointing: enabled")
            except Exception as e:
                print(f"  Gradient checkpointing: not available ({e})")

        # ===== 3. Backbone fine-tune strategy =====
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False
            print("  Strategy: frozen backbone")
        elif use_lora:
            self._apply_lora(lora_r, lora_alpha, lora_dropout, lora_target_modules)
        else:
            print("  Strategy: full fine-tuning (all params trainable)")

        # ===== 4. Classification Head (operates on token sequence) =====
        self.head = create_head(
            head_type=head_type,
            input_dim=self.hidden_dim,
            num_classes=num_classes,
            config=head_config or {},
        )
        print(f"  Head type: {head_type}")

        # Print parameter counts
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        print(f"  Total params:     {total:,}")
        print(f"  Trainable params: {trainable:,} ({100 * trainable / total:.2f}%)")

    def _apply_lora(self, r, alpha, dropout, target_modules):
        """Apply LoRA adapters to backbone. Compatible with peft 0.5.0+."""
        try:
            from peft import LoraConfig, get_peft_model
        except ImportError as e:
            raise ImportError(f"peft not installed: {e}")

        if target_modules is None:
            target_modules = ["query", "key", "value"]

        # Handle TaskType compatibility (may not exist in older peft)
        lora_kwargs = dict(
            r=r,
            lora_alpha=alpha,
            lora_dropout=dropout,
            target_modules=target_modules,
            bias="none",
        )
        try:
            from peft import TaskType
            lora_kwargs["task_type"] = TaskType.FEATURE_EXTRACTION
        except (ImportError, AttributeError):
            pass  # older peft — skip task_type

        lora_config = LoraConfig(**lora_kwargs)
        self.backbone = get_peft_model(self.backbone, lora_config)

        print("  Strategy: LoRA")
        if hasattr(self.backbone, "print_trainable_parameters"):
            self.backbone.print_trainable_parameters()

    def forward(self, input_ids, attention_mask=None):
        """
        Args:
            input_ids: [batch, seq_len]
            attention_mask: [batch, seq_len]
        Returns:
            logits: [batch, num_classes]
        """
        # ===== Backbone: get token-level embeddings =====
        outputs = self.backbone(
            input_ids=input_ids,
            attention_mask=attention_mask,
            output_hidden_states=False,
        )

        # outputs.last_hidden_state: [batch, seq_len, hidden_dim]
        token_embeddings = outputs.last_hidden_state

        # ===== Classification Head: operates on FULL token sequence =====
        # NO mean pooling! [batch, seq_len, hidden_dim] → head → [batch, num_classes]
        logits = self.head(token_embeddings, attention_mask)

        return logits

    def get_backbone_params(self):
        """Return backbone parameters (for separate LR group)."""
        return [p for n, p in self.named_parameters()
                if "backbone" in n and p.requires_grad]

    def get_head_params(self):
        """Return head parameters (for separate LR group)."""
        return [p for n, p in self.named_parameters()
                if "head" in n and p.requires_grad]

    def freeze_backbone(self):
        """Temporarily freeze backbone (for Phase 1 training)."""
        for n, p in self.named_parameters():
            if "backbone" in n:
                p.requires_grad = False

    def unfreeze_backbone(self):
        """Unfreeze backbone (for Phase 2 training)."""
        # Only unfreeze LoRA params or all params depending on config
        for n, p in self.named_parameters():
            if "backbone" in n:
                # For LoRA: only lora_ params should be unfrozen
                if "lora_" in n or "modules_to_save" in n:
                    p.requires_grad = True
                # If not using LoRA and it was frozen for phase1, unfreeze all
                elif not any("lora_" in nn for nn, _ in self.named_parameters()):
                    p.requires_grad = True


# ============================================================
# Shallow Transformer Classifier (MetaTransformer-style ablation)
# ============================================================

class ShallowTransformerClassifier(nn.Module):
    """
    Single-layer Transformer with learned embeddings, trained from scratch.
    Uses the same 6-mer tokenizer as NT-v2 to isolate the effect of
    the pre-trained 29-layer backbone vs a simple shallow encoder.

    Architecture mirrors MetaTransformer (Wichmann 2023):
      - Learned token embeddings (from scratch)
      - Learned positional embeddings
      - 1-layer Transformer encoder (configurable)
      - Same classification head as GFM variant
    """

    def __init__(
        self,
        backbone_name: str,
        num_classes: int,
        head_type: str = "attention_pool",
        head_config: dict = None,
        d_model: int = 128,
        nhead: int = 2,
        d_ff: int = 512,
        num_layers: int = 1,
        dropout: float = 0.1,
        max_seq_len: int = 128,
        **kwargs,
    ):
        super().__init__()

        print(f"Loading tokenizer for vocab: {backbone_name}")
        tokenizer = AutoTokenizer.from_pretrained(
            backbone_name, trust_remote_code=True
        )
        vocab_size = tokenizer.vocab_size
        pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0

        self.hidden_dim = d_model

        print(f"  Shallow Transformer: d_model={d_model}, layers={num_layers}, "
              f"heads={nhead}, d_ff={d_ff}")
        print(f"  Vocab size: {vocab_size}, pad_id: {pad_id}")

        # Learned embeddings (from scratch)
        self.token_embedding = nn.Embedding(vocab_size, d_model, padding_idx=pad_id)
        self.position_embedding = nn.Embedding(max_seq_len, d_model)
        self.embed_norm = nn.LayerNorm(d_model)
        self.embed_dropout = nn.Dropout(dropout)

        # Initialize embeddings
        nn.init.normal_(self.token_embedding.weight, std=0.02)
        nn.init.normal_(self.position_embedding.weight, std=0.02)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_ff,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Classification head (same interface as GFM variant)
        self.head = create_head(
            head_type=head_type,
            input_dim=d_model,
            num_classes=num_classes,
            config=head_config or {},
        )
        print(f"  Head type: {head_type}")

        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        print(f"  Total params:     {total:,}")
        print(f"  Trainable params: {trainable:,} ({100 * trainable / total:.2f}%)")

    def forward(self, input_ids, attention_mask=None):
        batch_size, seq_len = input_ids.shape

        positions = torch.arange(seq_len, device=input_ids.device).unsqueeze(0)
        x = self.token_embedding(input_ids) + self.position_embedding(positions)
        x = self.embed_norm(x)
        x = self.embed_dropout(x)

        src_key_padding_mask = None
        if attention_mask is not None:
            src_key_padding_mask = (attention_mask == 0)

        x = self.encoder(x, src_key_padding_mask=src_key_padding_mask)

        logits = self.head(x, attention_mask)
        return logits

    def get_backbone_params(self):
        """Return embedding + encoder parameters."""
        backbone_parts = [
            "token_embedding", "position_embedding",
            "embed_norm", "embed_dropout", "encoder",
        ]
        return [
            p for n, p in self.named_parameters()
            if any(bp in n for bp in backbone_parts) and p.requires_grad
        ]

    def get_head_params(self):
        return [
            p for n, p in self.named_parameters()
            if "head" in n and p.requires_grad
        ]

    def freeze_backbone(self):
        for n, p in self.named_parameters():
            if "head" not in n:
                p.requires_grad = False

    def unfreeze_backbone(self):
        for p in self.parameters():
            p.requires_grad = True


# ============================================================
# Factory
# ============================================================

def create_model(cfg: dict, num_classes: int):
    """Create model from config dict. Supports 'gfm' and 'shallow_transformer'."""
    model_type = cfg.get("type", "gfm")
    backbone_name = cfg["backbone"]

    if model_type == "shallow_transformer":
        shallow_cfg = cfg.get("shallow_config", {})
        return ShallowTransformerClassifier(
            backbone_name=backbone_name,
            num_classes=num_classes,
            head_type=cfg.get("head_type", "attention_pool"),
            head_config=cfg.get("head_config", {}),
            d_model=shallow_cfg.get("d_model", 128),
            nhead=shallow_cfg.get("nhead", 2),
            d_ff=shallow_cfg.get("d_ff", 512),
            num_layers=shallow_cfg.get("num_layers", 1),
            dropout=shallow_cfg.get("dropout", 0.1),
            max_seq_len=cfg.get("max_seq_len", 128),
        )
    else:
        return TokenLevelGFMClassifier(
            backbone_name=backbone_name,
            num_classes=num_classes,
            head_type=cfg.get("head_type", "transformer"),
            head_config=cfg.get("head_config", {}),
            freeze_backbone=cfg.get("freeze_backbone", False),
            use_lora=cfg.get("use_lora", True),
            lora_r=cfg.get("lora_r", 16),
            lora_alpha=cfg.get("lora_alpha", 32),
            lora_dropout=cfg.get("lora_dropout", 0.05),
            lora_target_modules=cfg.get("lora_target_modules"),
            gradient_checkpointing=cfg.get("gradient_checkpointing", True),
        )

