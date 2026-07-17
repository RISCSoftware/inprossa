from transformers import ViTConfig, ViTModel

# model_name = "WinKawaks/vit-tiny-patch16-224"  # smallest common ViT (~5.7M params)
model_name = "facebook/deit-tiny-patch16-224"
model = ViTModel.from_pretrained(model_name)
cfg: ViTConfig = model.config

print(f"Model: {model_name}")
print(f"  hidden_size (d_model):    {cfg.hidden_size}")
print(f"  num_hidden_layers:        {cfg.num_hidden_layers}")
print(f"  num_attention_heads:      {cfg.num_attention_heads}")
print(f"  head_dim:                 {cfg.hidden_size // cfg.num_attention_heads}")
print(f"  intermediate_size (MLP):  {cfg.intermediate_size}")
print(f"  mlp_ratio:                {cfg.intermediate_size / cfg.hidden_size:.1f}x")
print(f"  image_size:               {cfg.image_size}")
print(f"  patch_size:               {cfg.patch_size}")
print(f"  num_patches:              {(cfg.image_size // cfg.patch_size) ** 2}")
print(f"  num_channels:             {cfg.num_channels}")
print(f"  hidden_act:               {cfg.hidden_act}")
print(f"  layer_norm_eps:           {cfg.layer_norm_eps}")
print(f"  attention_probs_dropout:  {cfg.attention_probs_dropout_prob}")
print(f"  hidden_dropout:           {cfg.hidden_dropout_prob}")

n_params = sum(p.numel() for p in model.parameters())
print(f"\n  Total params: {n_params:,}  ({n_params/1e6:.2f}M)")


# Model: WinKawaks/vit-tiny-patch16-224
#   hidden_size (d_model):    192
#   num_hidden_layers:        12
#   num_attention_heads:      3
#   head_dim:                 64
#   intermediate_size (MLP):  768
#   mlp_ratio:                4.0x
#   image_size:               224
#   patch_size:               16
#   num_patches:              196
#   num_channels:             3
#   hidden_act:               gelu
#   layer_norm_eps:           1e-12
#   attention_probs_dropout:  0.0
#   hidden_dropout:           0.0

# Model: facebook/deit-tiny-patch16-224
#   hidden_size (d_model):    192
#   num_hidden_layers:        12
#   num_attention_heads:      3
#   head_dim:                 64
#   intermediate_size (MLP):  768
#   mlp_ratio:                4.0x
#   image_size:               224
#   patch_size:               16
#   num_patches:              196
#   num_channels:             3
#   hidden_act:               gelu
#   layer_norm_eps:           1e-12
#   attention_probs_dropout:  0.0
#   hidden_dropout:           0.0
