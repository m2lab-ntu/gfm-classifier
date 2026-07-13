#!/usr/bin/env python3
"""
Classification heads for Token-level GFM Classifier.

All heads receive [batch_size, seq_len, hidden_dim] token embeddings
(NOT mean-pooled) and produce [batch_size, num_classes] logits.

Four heads:
  1. TransformerClassificationHead — Lightweight Transformer + attention pooling
  2. CNNClassificationHead — Multi-scale 1D CNN
  3. AttentionPoolClassificationHead — Learnable attention pooling (simplest)
  4. MeanPoolClassificationHead — Mean pooling + MLP (baseline)
"""

import math
import torch
import torch.nn as nn


# ============================================================
# Head 0: Mean Pool + MLP (baseline — same as previous pipeline)
# ============================================================
class MeanPoolClassificationHead(nn.Module):
    """
    Simple mean-pool + MLP baseline.
    This should match the ~42% baseline from the embedding pipeline.
    Proves the backbone embeddings are working correctly.
    """

    def __init__(
        self,
        input_dim: int = 1024,
        num_classes: int = 120,
        hidden_dim: int = 512,
        dropout: float = 0.1,
        **kwargs,
    ):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, token_embeddings, attention_mask=None):
        # token_embeddings: [batch, seq_len, dim]
        # Mean pool over non-padding tokens
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()  # [batch, seq_len, 1]
            pooled = (token_embeddings * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            pooled = token_embeddings.mean(dim=1)
        return self.classifier(pooled)


# ============================================================
# Head 1: Lightweight Transformer + Attention Pooling
# ============================================================
class TransformerClassificationHead(nn.Module):
    """
    1-2 layer Transformer encoder on top of GFM token embeddings,
    followed by learnable attention-weighted pooling and classification.

    Uses a projection to a smaller dimension to reduce parameter count
    and improve optimization.
    """

    def __init__(
        self,
        input_dim: int = 1024,
        num_classes: int = 120,
        num_layers: int = 1,
        num_heads: int = 8,
        dim_feedforward: int = 512,
        proj_dim: int = 256,
        dropout: float = 0.1,
        **kwargs,  # absorb extra config keys
    ):
        super().__init__()
        # Project down from backbone dim to smaller dim for efficiency
        self.proj = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, proj_dim),
            nn.GELU(),
        )

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=proj_dim,
            nhead=num_heads,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,  # Pre-LN for more stable training
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers
        )

        # Learnable attention pooling (instead of mean pooling)
        self.attn_pool = nn.Linear(proj_dim, 1)

        self.classifier = nn.Sequential(
            nn.LayerNorm(proj_dim),
            nn.Dropout(dropout),
            nn.Linear(proj_dim, num_classes),
        )

    def forward(self, token_embeddings, attention_mask=None):
        # token_embeddings: [batch, seq_len, dim]

        # Project to smaller dimension
        x = self.proj(token_embeddings)  # [batch, seq_len, proj_dim]

        # Create src_key_padding_mask for transformer (True = ignored positions)
        src_key_padding_mask = None
        if attention_mask is not None:
            src_key_padding_mask = (attention_mask == 0)

        # Transformer layers
        x = self.transformer(
            x, src_key_padding_mask=src_key_padding_mask
        )

        # Attention pooling: learn which tokens matter
        attn_weights = self.attn_pool(x).squeeze(-1)  # [batch, seq_len]
        if attention_mask is not None:
            attn_weights = attn_weights.masked_fill(attention_mask == 0, float("-inf"))
        attn_weights = torch.softmax(attn_weights, dim=-1)  # [batch, seq_len]

        # Weighted sum: [batch, 1, seq_len] × [batch, seq_len, proj_dim] → [batch, proj_dim]
        pooled = torch.bmm(attn_weights.unsqueeze(1), x).squeeze(1)

        return self.classifier(pooled)


# ============================================================
# Head 2: Multi-scale 1D CNN
# ============================================================
class CNNClassificationHead(nn.Module):
    """
    Multi-scale 1D CNN (kernel sizes 3, 5, 7) on token embeddings,
    captures local patterns at different scales.
    """

    def __init__(
        self,
        input_dim: int = 1024,
        num_classes: int = 120,
        num_filters: int = 256,
        kernel_sizes: list = None,
        dropout: float = 0.1,
        **kwargs,
    ):
        super().__init__()
        if kernel_sizes is None:
            kernel_sizes = [3, 5, 7]

        self.convs = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Conv1d(input_dim, num_filters, kernel_size=k, padding=k // 2),
                    nn.BatchNorm1d(num_filters),
                    nn.GELU(),
                )
                for k in kernel_sizes
            ]
        )

        total_filters = num_filters * len(kernel_sizes)
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(total_filters, total_filters // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(total_filters // 2, num_classes),
        )

    def forward(self, token_embeddings, attention_mask=None):
        # token_embeddings: [batch, seq_len, dim]
        x = token_embeddings.transpose(1, 2)  # [batch, dim, seq_len] for Conv1d

        conv_outputs = []
        for conv in self.convs:
            c = conv(x)  # [batch, num_filters, seq_len]
            if attention_mask is not None:
                c = c * attention_mask.unsqueeze(1).float()
            c = c.max(dim=2)[0]  # Global max pooling: [batch, num_filters]
            conv_outputs.append(c)

        combined = torch.cat(conv_outputs, dim=1)  # [batch, total_filters]
        return self.classifier(combined)


# ============================================================
# Head 3: Attention Pooling (simplest)
# ============================================================
class AttentionPoolClassificationHead(nn.Module):
    """
    Learnable multi-head attention pooling without additional transformer layers.
    Simplest head — if this works well, it proves the value of token-level input.
    """

    def __init__(
        self,
        input_dim: int = 1024,
        num_classes: int = 120,
        hidden_dim: int = 512,
        num_attention_heads: int = 4,
        dropout: float = 0.1,
        **kwargs,
    ):
        super().__init__()
        self.num_heads = num_attention_heads
        self.head_dim = input_dim // num_attention_heads
        self.scale = self.head_dim ** -0.5

        # Learnable query tokens: [1, heads, head_dim]
        self.query = nn.Parameter(
            torch.randn(1, num_attention_heads, self.head_dim) * 0.02
        )
        self.k_proj = nn.Linear(input_dim, input_dim)
        self.v_proj = nn.Linear(input_dim, input_dim)

        self.classifier = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, token_embeddings, attention_mask=None):
        batch_size, seq_len, dim = token_embeddings.shape

        # Project keys and values
        k = (
            self.k_proj(token_embeddings)
            .view(batch_size, seq_len, self.num_heads, self.head_dim)
            .transpose(1, 2)
        )  # [batch, heads, seq_len, head_dim]
        v = (
            self.v_proj(token_embeddings)
            .view(batch_size, seq_len, self.num_heads, self.head_dim)
            .transpose(1, 2)
        )

        # Learnable query: [1, heads, head_dim] → [batch, heads, 1, head_dim]
        # FIX: self.query is already [1, heads, head_dim], expand batch then add seq dim
        q = self.query.expand(batch_size, -1, -1).unsqueeze(2)

        # Attention: [batch, heads, 1, seq_len]
        attn = (q @ k.transpose(-2, -1)) * self.scale

        if attention_mask is not None:
            attn = attn.masked_fill(
                attention_mask.unsqueeze(1).unsqueeze(2) == 0, float("-inf")
            )

        attn = torch.softmax(attn, dim=-1)

        # Weighted sum: [batch, heads, 1, head_dim] → [batch, heads, head_dim]
        out = (attn @ v).squeeze(2)
        out = out.reshape(batch_size, dim)  # [batch, dim]

        return self.classifier(out)


def create_head(head_type: str, input_dim: int, num_classes: int, config: dict = None):
    """Factory function to create a classification head."""
    config = config or {}
    if head_type == "transformer":
        return TransformerClassificationHead(
            input_dim=input_dim, num_classes=num_classes, **config
        )
    elif head_type == "cnn":
        return CNNClassificationHead(
            input_dim=input_dim, num_classes=num_classes, **config
        )
    elif head_type == "attention_pool":
        return AttentionPoolClassificationHead(
            input_dim=input_dim, num_classes=num_classes, **config
        )
    elif head_type == "mean_pool":
        return MeanPoolClassificationHead(
            input_dim=input_dim, num_classes=num_classes, **config
        )
    else:
        raise ValueError(f"Unknown head_type: {head_type}")

