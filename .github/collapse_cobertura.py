#!/usr/bin/env python3
"""
Collapse Cobertura coverage packages to a maximum depth.

- Reads an input Cobertura XML file (e.g., coverage.xml)
- Groups package names by the first N components separated by '.'
- Reassigns classes to the grouped packages and computes package line-rate
- Writes a new Cobertura XML file

Usage:
  python .github/collapse_cobertura.py INPUT_XML OUTPUT_XML [--max-depth 3]

Notes:
- Only standard library is used.
- Branch metrics are not recomputed (set to 0 if missing).
- Root attributes are preserved from the original XML.
"""
from __future__ import annotations

import argparse
import copy
import sys
import xml.etree.ElementTree as ET


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("input", help="Path to input Cobertura XML (coverage.xml)")
    p.add_argument("output", help="Path to output collapsed Cobertura XML")
    p.add_argument("--max-depth", type=int, default=3, help="Max package depth")
    return p.parse_args(argv)


def collapse_package_name(name: str, max_depth: int) -> str:
    parts = name.split(".") if name else []
    return ".".join(parts[:max_depth]) if parts else name


def compute_line_rate(pkg_el: ET.Element) -> float:
    total = 0
    covered = 0
    classes = pkg_el.find("classes")
    if classes is None:
        return 0.0
    for cls in classes.findall("class"):
        lines = cls.find("lines")
        if lines is None:
            continue
        for line in lines.findall("line"):
            total += 1
            try:
                hits = int(line.get("hits", "0"))
            except ValueError:
                hits = 0
            if hits > 0:
                covered += 1
    if total == 0:
        return 0.0
    return covered / float(total)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    tree = ET.parse(args.input)
    root = tree.getroot()

    # Build grouped packages
    packages = root.find("packages")
    if packages is None:
        # Nothing to do
        ET.ElementTree(root).write(args.output, encoding="utf-8", xml_declaration=True)
        return 0

    grouped: dict[str, ET.Element] = {}

    for pkg in packages.findall("package"):
        name = pkg.get("name", "")
        gname = collapse_package_name(name, args.max_depth)
        # Ensure target package exists
        if gname not in grouped:
            gpkg = ET.Element("package", {
                "name": gname,
                "line-rate": "0",
                "branch-rate": pkg.get("branch-rate", "0"),
                "complexity": pkg.get("complexity", "0"),
            })
            gclasses = ET.SubElement(gpkg, "classes")
            grouped[gname] = gpkg
        else:
            gpkg = grouped[gname]
            gclasses = gpkg.find("classes")
            if gclasses is None:
                gclasses = ET.SubElement(gpkg, "classes")

        # Move/copy classes into group
        classes = pkg.find("classes")
        if classes is not None:
            for cls in classes.findall("class"):
                gclasses = gpkg.find("classes")
                if gclasses is None:
                    gclasses = ET.SubElement(gpkg, "classes")
                gclasses.append(copy.deepcopy(cls))

    # Recompute line-rate for each grouped package
    for gpkg in grouped.values():
        lr = compute_line_rate(gpkg)
        gpkg.set("line-rate", f"{lr:.4f}")

    # Build new root preserving attributes
    new_root = ET.Element("coverage", root.attrib)
    # copy children we don't modify (e.g., sources)
    for child in root:
        if child.tag not in {"packages"}:
            new_root.append(copy.deepcopy(child))

    new_packages = ET.SubElement(new_root, "packages")
    # Sort by package name for a stable output
    for name in sorted(grouped.keys()):
        new_packages.append(grouped[name])

    ET.ElementTree(new_root).write(args.output, encoding="utf-8", xml_declaration=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
