"""Label remap for the duplicate Roboflow class list."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
sys.path.insert(0, str(ROOT / "ai" / "scripts"))

from prepare_dataset import parse_names, prepare_dataset, remap_plan, rewrite_label_line  # noqa: E402


PUBLISHED = """
train: train/images
val: valid/images
nc: 7
names: ['Drowning', 'Out of Water', 'Swimming', 'drowning', 'out of water', 'person', 'swimming']
"""


def test_parse_flow_names():
    names = parse_names(PUBLISHED)
    assert names[0] == "Drowning"
    assert names[-1] == "swimming"
    assert len(names) == 7


def test_remap_plan_collapses_to_four():
    names, id_map = remap_plan(parse_names(PUBLISHED))
    assert names == ["drowning", "out_of_water", "swimming", "person"]
    assert id_map[0] == id_map[3] == 0
    assert id_map[1] == id_map[4]
    assert id_map[2] == id_map[6]
    assert len(set(id_map.values())) == 4


def test_rewrite_label_line():
    _, id_map = remap_plan(parse_names(PUBLISHED))
    assert rewrite_label_line("3 0.5 0.5 0.2 0.2", id_map) == "0 0.5 0.5 0.2 0.2"
    assert rewrite_label_line("", id_map) is None


def test_prepare_dataset_symlinks_and_rewrites(tmp_path: Path):
    src = tmp_path / "src"
    images = src / "train" / "images"
    labels = src / "train" / "labels"
    images.mkdir(parents=True)
    labels.mkdir(parents=True)
    (images / "a.jpg").write_bytes(b"not-a-real-image")
    (labels / "a.txt").write_text("0 0.1 0.1 0.2 0.2\n6 0.4 0.4 0.1 0.1\n", encoding="utf-8")
    (src / "data.yaml").write_text(PUBLISHED, encoding="utf-8")
    dst = tmp_path / "dst"
    yaml_path = prepare_dataset(src, dst)
    text = (dst / "train" / "labels" / "a.txt").read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("0 ")
    assert text.splitlines()[1].startswith("2 ")
    assert "drowning" in yaml_path.read_text(encoding="utf-8")
    assert (dst / "train" / "images" / "a.jpg").exists()
