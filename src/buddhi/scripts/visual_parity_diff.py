"""Pure-Python visual telemetry, scene metrics, and parity diffing.

Ported from visual-parity-diff.mjs in @dzhng/skills (MIT License).
Operates using pure Python stdlib (struct, zlib, math) with zero external binary dependencies.
"""

from __future__ import annotations

import json
import math
import os
import struct
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass
class RawImage:
    width: int
    height: int
    data: bytearray  # RGBA bytearray (width * height * 4)


def _chunk(chunk_type: bytes, data: bytes) -> bytes:
    length = struct.pack(">I", len(data))
    crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    return length + chunk_type + data + crc


def encode_png_rgba(width: int, height: int, data: bytearray | bytes) -> bytes:
    """Encode raw RGBA buffer into standard 8-bit PNG bytes."""
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = _chunk(b"IHDR", header)

    # Prepend filter byte 0 (None) to each row
    stride = width * 4
    raw_scanlines = bytearray()
    for y in range(height):
        raw_scanlines.append(0)  # Filter byte None
        start = y * stride
        raw_scanlines.extend(data[start : start + stride])

    compressed = zlib.compress(bytes(raw_scanlines), level=6)
    idat = _chunk(b"IDAT", compressed)
    iend = _chunk(b"IEND", b"")
    return PNG_SIGNATURE + ihdr + idat + iend


def _paeth_predict(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png(stream: bytes) -> RawImage:
    """Decode standard PNG bytes into a RawImage (RGBA 8-bit)."""
    if not stream.startswith(PNG_SIGNATURE):
        raise ValueError("Invalid PNG signature")

    pos = len(PNG_SIGNATURE)
    width = 0
    height = 0
    bit_depth = 0
    color_type = 0
    palette: list[tuple[int, int, int]] = []
    idat_chunks: list[bytes] = []

    while pos < len(stream):
        if pos + 8 > len(stream):
            break
        length = struct.unpack(">I", stream[pos : pos + 4])[0]
        chunk_type = stream[pos + 4 : pos + 8]
        data = stream[pos + 8 : pos + 8 + length]
        pos += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", data[:10])
            if bit_depth != 8:
                raise ValueError(f"Unsupported PNG bit depth: {bit_depth}")
        elif chunk_type == b"PLTE":
            for i in range(0, len(data), 3):
                palette.append((data[i], data[i + 1], data[i + 2]))
        elif chunk_type == b"IDAT":
            idat_chunks.append(data)
        elif chunk_type == b"IEND":
            break

    if width == 0 or height == 0:
        raise ValueError("PNG missing IHDR or zero dimensions")

    decompressed = zlib.decompress(b"".join(idat_chunks))

    # Channels per pixel based on color type
    # 0: Grayscale (1), 2: RGB (3), 3: Palette (1), 4: Gray+Alpha (2), 6: RGBA (4)
    channels_map = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    if color_type not in channels_map:
        raise ValueError(f"Unsupported PNG color type: {color_type}")
    channels = channels_map[color_type]
    stride = width * channels

    expected_len = height * (stride + 1)
    if len(decompressed) < expected_len:
        raise ValueError("Corrupt decompressed PNG payload size")

    raw_rgba = bytearray(width * height * 4)
    prev_row = bytearray(stride)
    in_pos = 0

    for y in range(height):
        filter_type = decompressed[in_pos]
        in_pos += 1
        curr_row = bytearray(decompressed[in_pos : in_pos + stride])
        in_pos += stride

        if filter_type == 1:  # Sub
            for x in range(channels, stride):
                curr_row[x] = (curr_row[x] + curr_row[x - channels]) & 0xFF
        elif filter_type == 2:  # Up
            for x in range(stride):
                curr_row[x] = (curr_row[x] + prev_row[x]) & 0xFF
        elif filter_type == 3:  # Average
            for x in range(stride):
                left = curr_row[x - channels] if x >= channels else 0
                up = prev_row[x]
                curr_row[x] = (curr_row[x] + ((left + up) >> 1)) & 0xFF
        elif filter_type == 4:  # Paeth
            for x in range(stride):
                left = curr_row[x - channels] if x >= channels else 0
                up = prev_row[x]
                up_left = prev_row[x - channels] if x >= channels else 0
                curr_row[x] = (curr_row[x] + _paeth_predict(left, up, up_left)) & 0xFF

        prev_row = curr_row

        # Convert curr_row to RGBA
        out_offset = y * width * 4
        if color_type == 6:  # RGBA
            raw_rgba[out_offset : out_offset + stride] = curr_row
        elif color_type == 2:  # RGB
            for x in range(width):
                si = x * 3
                di = out_offset + x * 4
                raw_rgba[di] = curr_row[si]
                raw_rgba[di + 1] = curr_row[si + 1]
                raw_rgba[di + 2] = curr_row[si + 2]
                raw_rgba[di + 3] = 255
        elif color_type == 0:  # Grayscale
            for x in range(width):
                val = curr_row[x]
                di = out_offset + x * 4
                raw_rgba[di] = val
                raw_rgba[di + 1] = val
                raw_rgba[di + 2] = val
                raw_rgba[di + 3] = 255
        elif color_type == 4:  # Gray + Alpha
            for x in range(width):
                val = curr_row[x * 2]
                alpha = curr_row[x * 2 + 1]
                di = out_offset + x * 4
                raw_rgba[di] = val
                raw_rgba[di + 1] = val
                raw_rgba[di + 2] = val
                raw_rgba[di + 3] = alpha
        elif color_type == 3:  # Palette
            for x in range(width):
                idx = curr_row[x]
                r, g, b = palette[idx] if idx < len(palette) else (0, 0, 0)
                di = out_offset + x * 4
                raw_rgba[di] = r
                raw_rgba[di + 1] = g
                raw_rgba[di + 2] = b
                raw_rgba[di + 3] = 255

    return RawImage(width=width, height=height, data=raw_rgba)


def luminance(r: float, g: float, b: float) -> float:
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def is_terrain_like(r: float, g: float, b: float) -> bool:
    return g > 72 and r > 62 and b > 38 and r > b * 0.92 and g > b * 0.92


def compute_scene_metrics(img: RawImage) -> dict[str, Any] | None:
    """Compute coarse-grid scene composition metrics for an image."""
    step_x = max(1, img.width // 160)
    step_y = max(1, img.height // 90)
    cols = img.width // step_x
    rows = img.height // step_y
    if cols < 2 or rows < 2:
        return None

    gray_samples: list[float] = []
    buckets: dict[tuple[int, int, int], int] = {}
    samples = 0
    transparent = 0

    for gy in range(rows):
        for gx in range(cols):
            o = (gy * step_y * img.width + gx * step_x) * 4
            alpha = img.data[o + 3] / 255.0
            if alpha == 0:
                transparent += 1
            r = img.data[o] * alpha
            g = img.data[o + 1] * alpha
            b = img.data[o + 2] * alpha
            lum = luminance(r, g, b)
            gray_samples.append(lum)

            bucket = (int(r) >> 4, int(g) >> 4, int(b) >> 4)
            buckets[bucket] = buckets.get(bucket, 0) + 1
            samples += 1

    sorted_gray = sorted(gray_samples)
    mean = sum(sorted_gray) / len(sorted_gray)
    p5 = sorted_gray[int(len(sorted_gray) * 0.05)]
    p95 = sorted_gray[int(len(sorted_gray) * 0.95)]

    entropy = 0.0
    dominant = 0
    for count in buckets.values():
        p = count / samples
        entropy -= p * math.log2(p)
        dominant = max(dominant, count)

    edges = 0
    checked = 0
    for gy in range(rows - 1):
        for gx in range(cols - 1):
            i = gy * cols + gx
            dx = abs(gray_samples[i] - gray_samples[i + 1])
            dy = abs(gray_samples[i] - gray_samples[i + cols])
            if max(dx, dy) > 12:
                edges += 1
            checked += 1

    return {
        "colorBuckets": len(buckets),
        "colorEntropyBits": round(entropy, 4),
        "edgeDensity": round(edges / checked if checked else 0, 4),
        "dominantColorShare": round(dominant / samples if samples else 0, 4),
        "transparentShare": round(transparent / samples if samples else 0, 4),
        "luminanceMean": round(mean, 4),
        "luminanceP5": round(p5, 4),
        "luminanceP95": round(p95, 4),
        "luminanceContrast": round(p95 - p5, 4),
    }


def sobel_magnitude(
    gray: list[float], width: int, height: int, x: int, y: int
) -> float:
    xm = max(0, x - 1)
    xp = min(width - 1, x + 1)
    ym = max(0, y - 1)
    yp = min(height - 1, y + 1)

    a = gray[ym * width + xm]
    b = gray[ym * width + x]
    c = gray[ym * width + xp]
    d = gray[y * width + xm]
    f = gray[y * width + xp]
    g = gray[yp * width + xm]
    h = gray[yp * width + x]
    i = gray[yp * width + xp]

    gx = (c + 2 * f + i) - (a + 2 * d + g)
    gy = (g + 2 * h + i) - (a + 2 * b + c)
    return min(255.0, math.sqrt(gx * gx + gy * gy))


def _safe_rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def run_visual_parity_diff(
    candidate_dir: Path,
    reference_dir: Path | None = None,
    out_dir: Path | None = None,
    repo_root: Path | None = None,
    report_order: list[str] | None = None,
    crops_json: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    """Run visual telemetry in solo mode or pair diff mode."""
    root = repo_root or Path.cwd()
    output_dir = out_dir or (root / "visual-diff")
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_root = output_dir.name

    if reference_dir is None:
        # Solo scene metrics mode
        candidate_files = sorted(
            [f for f in candidate_dir.glob("*.png") if f.is_file()]
        )
        if not candidate_files:
            return 1, {"error": f"no PNGs found in {candidate_dir}"}

        results: list[dict[str, Any]] = []
        for cfile in candidate_files:
            raw = decode_png(cfile.read_bytes())
            metrics = compute_scene_metrics(raw)
            results.append(
                {
                    "id": cfile.stem,
                    "image": _safe_rel(cfile, root),
                    "dimensions": {"width": raw.width, "height": raw.height},
                    "sceneMetrics": metrics,
                }
            )

        report = {
            "kind": "screenshot-scene-metrics",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "note": "Absolute per-image telemetry, no reference involved.",
            "imageCount": len(results),
            "results": results,
        }
        report_path = output_dir / "scene-metrics.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0, report

    # Pair diff mode
    curr_files = {f.name: f for f in reference_dir.glob("*.png") if f.is_file()}
    cand_files = {f.name: f for f in candidate_dir.glob("*.png") if f.is_file()}
    common_names = sorted(set(curr_files.keys()) & set(cand_files.keys()))

    if not common_names:
        return 1, {
            "error": f"no comparable PNG pairs found between {reference_dir} and {candidate_dir}"
        }

    results = []
    for name in common_names:
        pair_id = os.path.splitext(name)[0]
        curr_raw = decode_png(curr_files[name].read_bytes())
        cand_raw = decode_png(cand_files[name].read_bytes())

        if curr_raw.width != cand_raw.width or curr_raw.height != cand_raw.height:
            return 1, {
                "error": f"{pair_id}: image sizes differ: current={curr_raw.width}x{curr_raw.height} candidate={cand_raw.width}x{cand_raw.height}"
            }

        width, height = curr_raw.width, curr_raw.height
        total = width * height

        # Prepare diff artifacts
        gray_curr = bytearray(total * 4)
        gray_cand = bytearray(total * 4)
        abs_diff = bytearray(total * 4)
        side_by_side = bytearray(width * 2 * height * 4)
        edge_curr = bytearray(total * 4)
        edge_cand = bytearray(total * 4)
        edge_diff = bytearray(total * 4)
        pixelmatch_diff = bytearray(total * 4)

        current_gray_floats: list[float] = [0.0] * total
        candidate_gray_floats: list[float] = [0.0] * total

        sum_abs = 0.0
        sum_sq = 0.0
        over16 = 0
        over32 = 0
        over64 = 0
        black_curr = 0
        black_cand = 0
        terrain_curr = 0
        terrain_cand = 0
        lum_curr_sum = 0.0
        lum_cand_sum = 0.0
        pixelmatch_mismatch = 0

        for i in range(total):
            o = i * 4
            cg = luminance(curr_raw.data[o], curr_raw.data[o + 1], curr_raw.data[o + 2])
            wg = luminance(cand_raw.data[o], cand_raw.data[o + 1], cand_raw.data[o + 2])
            lum_curr_sum += cg
            lum_cand_sum += wg
            current_gray_floats[i] = cg
            candidate_gray_floats[i] = wg

            d = abs(cg - wg)
            sum_abs += d
            sum_sq += d * d
            if d > 16:
                over16 += 1
            if d > 32:
                over32 += 1
            if d > 64:
                over64 += 1
            if cg < 24:
                black_curr += 1
            if wg < 24:
                black_cand += 1
            if is_terrain_like(
                curr_raw.data[o], curr_raw.data[o + 1], curr_raw.data[o + 2]
            ):
                terrain_curr += 1
            if is_terrain_like(
                cand_raw.data[o], cand_raw.data[o + 1], cand_raw.data[o + 2]
            ):
                terrain_cand += 1

            # Pixelmatch emulation on grayscale RGBA buffers (threshold: 0.08 of 255 = 20.4)
            if d > 20.4:
                pixelmatch_mismatch += 1
                pixelmatch_diff[o] = 255
                pixelmatch_diff[o + 1] = 0
                pixelmatch_diff[o + 2] = 0
                pixelmatch_diff[o + 3] = 255
            else:
                dim = int(cg * 0.1)
                pixelmatch_diff[o] = dim
                pixelmatch_diff[o + 1] = dim
                pixelmatch_diff[o + 2] = dim
                pixelmatch_diff[o + 3] = 255

            icg = max(0, min(255, round(cg)))
            gray_curr[o : o + 4] = bytes([icg, icg, icg, 255])

            iwg = max(0, min(255, round(wg)))
            gray_cand[o : o + 4] = bytes([iwg, iwg, iwg, 255])

            heat = min(255, int(d * 4))
            abs_diff[o] = heat
            abs_diff[o + 1] = max(0, 160 - heat)
            abs_diff[o + 2] = max(0, 255 - heat)
            abs_diff[o + 3] = 255

            # Side-by-side composite
            x = i % width
            y = i // width
            s_curr_o = (y * (width * 2) + x) * 4
            side_by_side[s_curr_o : s_curr_o + 4] = curr_raw.data[o : o + 4]
            s_cand_o = (y * (width * 2) + (x + width)) * 4
            side_by_side[s_cand_o : s_cand_o + 4] = cand_raw.data[o : o + 4]

        # Sobel edge filter pass
        curr_energy = 0.0
        cand_energy = 0.0
        edge_diff_over32 = 0
        for y in range(height):
            for x in range(width):
                i = y * width + x
                o = i * 4
                ce = sobel_magnitude(current_gray_floats, width, height, x, y)
                we = sobel_magnitude(candidate_gray_floats, width, height, x, y)
                curr_energy += ce / 255.0
                cand_energy += we / 255.0
                ediff = abs(ce - we)
                if ediff > 32:
                    edge_diff_over32 += 1

                ice = max(0, min(255, round(ce)))
                edge_curr[o : o + 4] = bytes([ice, ice, ice, 255])
                iwe = max(0, min(255, round(we)))
                edge_cand[o : o + 4] = bytes([iwe, iwe, iwe, 255])

                edge_diff[o] = min(255, int(ediff * 4))
                edge_diff[o + 1] = max(0, int(180 - ediff * 3))
                edge_diff[o + 2] = max(0, int(255 - ediff * 4))
                edge_diff[o + 3] = 255

        curr_energy /= total
        cand_energy /= total
        floor = 1e-6
        if curr_energy < floor and cand_energy < floor:
            edge_energy_ratio = 1.0
        else:
            edge_energy_ratio = cand_energy / max(floor, curr_energy)

        diff_ratio32 = over32 / total
        pixelmatch_ratio = pixelmatch_mismatch / total
        edge_diff_ratio32 = edge_diff_over32 / total

        parity_distance = (
            0.35 * diff_ratio32
            + 0.25 * pixelmatch_ratio
            + 0.25 * edge_diff_ratio32
            + 0.15 * min(1.0, abs(math.log2(edge_energy_ratio)))
        )

        # Write out 8 diagnostic PNG artifacts
        (output_dir / f"{pair_id}-side-by-side.png").write_bytes(
            encode_png_rgba(width * 2, height, side_by_side)
        )
        (output_dir / f"{pair_id}-current-gray.png").write_bytes(
            encode_png_rgba(width, height, gray_curr)
        )
        (output_dir / f"{pair_id}-candidate-gray.png").write_bytes(
            encode_png_rgba(width, height, gray_cand)
        )
        (output_dir / f"{pair_id}-absdiff.png").write_bytes(
            encode_png_rgba(width, height, abs_diff)
        )
        (output_dir / f"{pair_id}-pixelmatch.png").write_bytes(
            encode_png_rgba(width, height, pixelmatch_diff)
        )
        (output_dir / f"{pair_id}-current-edges.png").write_bytes(
            encode_png_rgba(width, height, edge_curr)
        )
        (output_dir / f"{pair_id}-candidate-edges.png").write_bytes(
            encode_png_rgba(width, height, edge_cand)
        )
        (output_dir / f"{pair_id}-edge-diff.png").write_bytes(
            encode_png_rgba(width, height, edge_diff)
        )

        results.append(
            {
                "id": pair_id,
                "current": _safe_rel(curr_files[name], root),
                "candidate": _safe_rel(cand_files[name], root),
                "dimensions": {"width": width, "height": height},
                "parityDistance": round(parity_distance, 4),
                "sceneMetrics": {
                    "current": compute_scene_metrics(curr_raw),
                    "candidate": compute_scene_metrics(cand_raw),
                },
                "grayscale": {
                    "mae": round(sum_abs / total, 4),
                    "rmse": round(math.sqrt(sum_sq / total), 4),
                    "diffRatio16": round(over16 / total, 4),
                    "diffRatio32": round(diff_ratio32, 4),
                    "diffRatio64": round(over64 / total, 4),
                    "pixelmatchRatio": round(pixelmatch_ratio, 4),
                },
                "contentProxies": {
                    "blackRatioCurrent": round(black_curr / total, 4),
                    "blackRatioCandidate": round(black_cand / total, 4),
                    "terrainLikeRatioCurrent": round(terrain_curr / total, 4),
                    "terrainLikeRatioCandidate": round(terrain_cand / total, 4),
                    "avgLuminanceCurrent": round(lum_curr_sum / total, 4),
                    "avgLuminanceCandidate": round(lum_cand_sum / total, 4),
                    "avgLuminanceDelta": round(
                        (lum_cand_sum - lum_curr_sum) / total, 4
                    ),
                    "edgeEnergyCurrent": round(curr_energy, 4),
                    "edgeEnergyCandidate": round(cand_energy, 4),
                    "edgeEnergyRatio": round(edge_energy_ratio, 4),
                    "edgeDiffRatio32": round(edge_diff_ratio32, 4),
                },
                "artifacts": {
                    "sideBySide": f"{artifact_root}/{pair_id}-side-by-side.png",
                    "currentGray": f"{artifact_root}/{pair_id}-current-gray.png",
                    "candidateGray": f"{artifact_root}/{pair_id}-candidate-gray.png",
                    "absDiff": f"{artifact_root}/{pair_id}-absdiff.png",
                    "pixelmatch": f"{artifact_root}/{pair_id}-pixelmatch.png",
                    "currentEdges": f"{artifact_root}/{pair_id}-current-edges.png",
                    "candidateEdges": f"{artifact_root}/{pair_id}-candidate-edges.png",
                    "edgeDiff": f"{artifact_root}/{pair_id}-edge-diff.png",
                },
            }
        )

    results.sort(key=lambda r: float(r["parityDistance"]), reverse=True)
    report = {
        "kind": "screenshot-parity-diff",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": "Lower parityDistance means closer to reference.",
        "pairCount": len(results),
        "worstPair": results[0]["id"] if results else None,
        "results": results,
    }
    report_path = output_dir / "visual-parity-diff.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0, report


def selftest() -> tuple[int, str]:
    """Verify PNG encode/decode roundtrip and metrics calculation."""
    # Synthetic 4x4 image
    width, height = 4, 4
    raw_data = bytearray(width * height * 4)
    for i in range(width * height):
        raw_data[i * 4] = (i * 16) & 0xFF
        raw_data[i * 4 + 1] = (i * 32) & 0xFF
        raw_data[i * 4 + 2] = (i * 48) & 0xFF
        raw_data[i * 4 + 3] = 255

    encoded = encode_png_rgba(width, height, raw_data)
    decoded = decode_png(encoded)
    assert decoded.width == width
    assert decoded.height == height
    assert decoded.data == raw_data

    # Compare identical images
    metrics = compute_scene_metrics(decoded)
    assert metrics is not None
    assert "colorBuckets" in metrics
    return 0, "selftest: visual-parity-diff OK"
