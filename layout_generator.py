import csv
import argparse

try:
    from pyaedt import Edb
except ImportError:  # pragma: no cover - library missing at runtime
    Edb = None


def parse_stackup(csv_path):
    """Read stackup information from a CSV file."""
    stack = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not row.get('Design Layer Name'):
                continue
            row['thickness_mm'] = float(row['Thickness (um)']) * 1e-3
            stack.append(row)
    return stack


def build_stackup(edb, stack):
    """Create stackup and materials in the EDB."""
    for layer in stack:
        mat = layer['Material']
        if Edb and mat not in edb.materials.material_keys:
            edb.materials.add_material(
                mat,
                permittivity=float(layer['Relative Permittivity']),
                permeability=float(layer['Relative Permeability']),
                conductivity=float(layer['Bulk Conductivity']),
                dielectric_loss=float(layer['Dielectric Loss Tangent']),
                magnetic_loss=float(layer['Magnetic Loss Tangent']),
            )
        if Edb:
            edb.stackup.add_layer(
                layer['Design Layer Name'],
                layer_type=layer['Type'],
                material=mat,
                thickness=str(layer['thickness_mm']) + "mm",
            )


def add_differential_pair(edb, args):
    """Create a differential pair with meanders on L03_SIG1."""
    if not Edb:
        return
    modeler = edb.modeler
    layer = "L03_SIG1"
    w = args.width
    gap = args.gap
    start_x = 0.0
    start_y = 0.0
    p_net = "diff_p"
    n_net = "diff_n"

    def create_trace(offset):
        pts = []
        x = start_x
        y = start_y + offset
        pts.append([x, y])
        for _ in range(args.intra_count):
            x += args.intra_height
            pts.append([x, y])
            y += args.intra_height
            pts.append([x, y])
            x += args.intra_height
            pts.append([x, y])
            y -= args.intra_height
            pts.append([x, y])
        return pts

    pos_pts = create_trace((w + gap) / 2.0)
    neg_pts = create_trace(-(w + gap) / 2.0)
    modeler.create_trace(pos_pts, layer, w, p_net)
    modeler.create_trace(neg_pts, layer, w, n_net)


def main():
    parser = argparse.ArgumentParser(description="Generate layout from CSV stackup")
    parser.add_argument("csv", help="Path to stackup CSV file")
    parser.add_argument("output", help="Output EDB folder")
    parser.add_argument("--width", type=float, required=True, help="Trace width in mm")
    parser.add_argument("--gap", type=float, required=True, help="Gap between differential traces in mm")
    parser.add_argument("--gap_to_ground", type=float, default=0.0, help="Gap to ground in mm")
    parser.add_argument("--intra_height", type=float, default=0.5, help="Meander height inside each trace in mm")
    parser.add_argument("--intra_count", type=int, default=1, help="Number of intra-trace meanders")
    parser.add_argument("--inter_height", type=float, default=0.5, help="Meander height between traces in mm")
    parser.add_argument("--inter_count", type=int, default=1, help="Number of inter-trace meanders")
    parser.add_argument("--edb_version", default=None, help="Target Ansys version")
    args = parser.parse_args()

    stack = parse_stackup(args.csv)

    if not Edb:
        raise RuntimeError("pyaedt is required to run this script")

    with Edb(args.output, edbversion=args.edb_version, new=True) as edb:
        build_stackup(edb, stack)
        add_differential_pair(edb, args)
        edb.save()


if __name__ == "__main__":
    main()
