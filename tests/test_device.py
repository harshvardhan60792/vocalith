from vocalith.device import pick_device, pick_dtype, describe_device


def test_pick_device_returns_valid_value():
    assert pick_device() in ("cuda", "mps", "cpu")


def test_pick_dtype_cpu_is_float32():
    import torch
    assert pick_dtype("cpu") == torch.float32


def test_describe_device_shape():
    info = describe_device()
    assert set(info) == {"device", "is_gpu", "name", "vram_gb"}
    assert isinstance(info["is_gpu"], bool)
