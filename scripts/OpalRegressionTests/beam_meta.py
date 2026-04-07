"""
Parse OPAL stdout (simname.out) for per-beam / per-container metadata printed by
Beam::print and TrackRun::execute, then align rows with regression stat stems.
"""

from __future__ import annotations

import math
import os
import re
from typing import Any, Optional

# Electron rest energy [eV] (CODATA 2018)
_ELECTRON_REST_EV = 510998.9461

# OPAL-X prefixes each stdout line with a prompt; strip before matching Beam banners.
_OPAL_PROMPT_RE = re.compile(r"^OPAL-X(?:\[\d+\])?>\s*")


def _strip_opal_prompt(line: str) -> str:
    m = _OPAL_PROMPT_RE.match(line)
    if m:
        return line[m.end() :]
    return line


def _strip_num(s: str) -> str:
    return s.strip()


def parse_beam_blocks(log_text: str) -> list[dict[str, Any]]:
    """
    Split log into Beam::print sections and extract banner fields.
    """
    lines = log_text.splitlines()
    blocks: list[dict[str, Any]] = []
    i = 0
    start_re = re.compile(r"^\*\s+\*+\s+B\s+E\s+A\s+M\s+\*+")
    # Closing banner: "* " then only asterisks (and trailing whitespace) to EOL
    end_re = re.compile(r"^\*\s+\*+\s*$")

    while i < len(lines):
        raw = lines[i]
        norm = _strip_opal_prompt(raw)
        if start_re.match(norm):
            i += 1
            cur: dict[str, Any] = {}
            while i < len(lines):
                norm_i = _strip_opal_prompt(lines[i])
                if end_re.match(norm_i) and "beam_name" in cur:
                    blocks.append(cur)
                    i += 1
                    break
                line = norm_i
                m = re.match(r"^\*\s+BEAM\s+(\S+)\s*$", line)
                if m:
                    cur["beam_name"] = m.group(1)
                m = re.match(r"^\*\s+PARTICLE\s+(\S+)\s*$", line)
                if m:
                    cur["species"] = m.group(1)
                m = re.match(r"^\*\s+REST MASS\s+(\S+)\s+\[GeV\]\s*$", line)
                if m:
                    cur["rest_mass_GeV"] = m.group(1)
                m = re.match(r"^\*\s+CHARGE\s+(.+?)\s*$", line)
                if m:
                    cur["charge_line"] = m.group(1).strip()
                m = re.match(r"^\*\s+MOMENTUM\s+(.+?)\s+\[eV/c\]\s*$", line)
                if m:
                    cur["momentum_eV_c"] = _strip_num(m.group(1))
                m = re.match(r"^\*\s+MOMENTUM\s+(.+?)\s+\[GeV/c\]\s*$", line)
                if m:
                    cur["momentum_GeV_c"] = _strip_num(m.group(1))
                m = re.match(r"^\*\s+CURRENT\s+(.+?)\s+\[A\]\s*$", line)
                if m:
                    cur["beam_current_A"] = _strip_num(m.group(1))
                m = re.match(r"^\*\s+FREQUENCY\s+(.+?)\s+\[MHz\]\s*$", line)
                if m:
                    cur["rf_frequency_MHz"] = _strip_num(m.group(1))
                m = re.match(r"^\*\s+NPART\s+(\S+)\s*$", line)
                if m:
                    cur["n_macroparticles"] = m.group(1)
                i += 1
            continue
        i += 1
    return blocks


def parse_trackrun_extras(log_text: str) -> dict[int, dict[str, str]]:
    """
    Lines from TrackRun after each beam: macro charge, mass, particles per macro.
    """
    out: dict[int, dict[str, str]] = {}
    pat_charge = re.compile(
        r"^\*\s+Beam\[(\d+)\]\s+\S+\s+macro charge per particle \[C\]:\s*(.+?)\s*$"
    )
    pat_mass = re.compile(
        r"^\*\s+Beam\[(\d+)\]\s+\S+\s+macro mass per particle \[GeV/c\^2\]:\s*(.+?)\s*$"
    )
    pat_ratio = re.compile(
        r"^\*\s+Beam\[(\d+)\]\s+\S+\s+particles per macro particle:\s*(\S+)\s*$"
    )
    for line in log_text.splitlines():
        line = _strip_opal_prompt(line)
        m = pat_charge.match(line)
        if m:
            idx = int(m.group(1))
            out.setdefault(idx, {})["macro_charge_per_particle_C"] = m.group(2).strip()
            continue
        m = pat_mass.match(line)
        if m:
            idx = int(m.group(1))
            out.setdefault(idx, {})["macro_mass_GeV_c2"] = m.group(2).strip()
            continue
        m = pat_ratio.match(line)
        if m:
            idx = int(m.group(1))
            out.setdefault(idx, {})["particles_per_macroparticle"] = m.group(2).strip()
    return out


def _starting_energy_gev(species: str, p_evc_str: str, rest_mass_gev_str: Optional[str]) -> str:
    """Kinetic + rest in GeV when we can evaluate; else em dash."""
    if not p_evc_str:
        return "—"
    try:
        p_evc = float(p_evc_str)
    except ValueError:
        return "—"
    sp = (species or "").upper()
    m_ev = None
    if sp == "ELECTRON":
        m_ev = _ELECTRON_REST_EV
    elif rest_mass_gev_str:
        try:
            m_gev = float(rest_mass_gev_str)
            m_ev = m_gev * 1.0e9
        except ValueError:
            pass
    if m_ev is None:
        return "—"
    e_ev = math.sqrt(p_evc * p_evc + m_ev * m_ev)
    return str(e_ev / 1.0e9)


def merge_beam_metadata(
    beam_blocks: list[dict[str, Any]], extras: dict[int, dict[str, str]]
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for i, b in enumerate(beam_blocks):
        row = dict(b)
        ex = extras.get(i, {})
        row.update(ex)
        merged.append(row)
    return merged


def attach_stat_stems(
    beams: list[dict[str, Any]], stat_stems: list[str], simname: str
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """
    Add stat_stem to each beam row. stat_stems order matches discover_stat_stems
    (simname first if present, then _c0, _c1, ...).
    """
    warning: Optional[str] = None
    if len(beams) != len(stat_stems):
        warning = (
            "beam_metadata: parsed %d beam(s) but reference has %d stat stem(s); "
            "stat_stem alignment may be wrong"
            % (len(beams), len(stat_stems))
        )
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(beams):
        r = dict(row)
        if i < len(stat_stems):
            r["stat_stem"] = stat_stems[i]
        else:
            r["stat_stem"] = None
        # Total macro bunch charge [C] ≈ q_macro * N
        q_s = r.get("macro_charge_per_particle_C")
        n_s = r.get("n_macroparticles")
        if q_s and n_s:
            try:
                qv = float(q_s)
                nv = float(n_s)
                r["total_macro_bunch_charge_C"] = str(qv * nv)
            except ValueError:
                r["total_macro_bunch_charge_C"] = "—"
        else:
            r["total_macro_bunch_charge_C"] = "—"
        species = r.get("species") or ""
        p_evc = r.get("momentum_eV_c") or ""
        rm = r.get("rest_mass_GeV")
        r["starting_energy_GeV"] = _starting_energy_gev(species, p_evc, rm)
        out_rows.append(r)
    return out_rows, warning


def build_beam_containers_json(
    log_text: str, stat_stems: list[str], simname: str
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """
    Full pipeline: parse log, merge TrackRun extras, attach stems, normalize keys for JSON.
    """
    blocks = parse_beam_blocks(log_text)
    if not blocks:
        return [], None
    extras = parse_trackrun_extras(log_text)
    merged = merge_beam_metadata(blocks, extras)
    rows, warn = attach_stat_stems(merged, stat_stems, simname)
    json_rows: list[dict[str, Any]] = []
    for r in rows:
        json_rows.append(
            {
                "stat_stem": r.get("stat_stem"),
                "beam_name": r.get("beam_name"),
                "species": r.get("species"),
                "momentum_eV_c": r.get("momentum_eV_c"),
                "momentum_GeV_c": r.get("momentum_GeV_c"),
                "starting_energy_GeV": r.get("starting_energy_GeV"),
                "beam_current_A": r.get("beam_current_A"),
                "macro_charge_per_particle_C": r.get("macro_charge_per_particle_C"),
                "n_macroparticles": r.get("n_macroparticles"),
                "particles_per_macroparticle": r.get("particles_per_macroparticle"),
                "rf_frequency_MHz": r.get("rf_frequency_MHz"),
                "total_macro_bunch_charge_C": r.get("total_macro_bunch_charge_C"),
                "rest_mass_GeV": r.get("rest_mass_GeV"),
                "charge_line": r.get("charge_line"),
            }
        )
    return json_rows, warn


def load_beam_containers_from_out(
    out_path: str, stat_stems: list[str], simname: str
) -> tuple[list[dict[str, Any]], Optional[str]]:
    if not out_path or not os.path.isfile(out_path):
        return [], None
    try:
        with open(out_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return [], None
    return build_beam_containers_json(text, stat_stems, simname)
