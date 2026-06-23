import json

notebook_path = "/global/homes/z/zhan391/code/ESP-Lab/jupyter/7_refactor_tc_analysis.ipynb"

with open(notebook_path, "r") as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        for i, line in enumerate(source):
            if "from workflows.tc_track_density import read_stitch_nodes_tracks" in line:
                source[i] = "import sys\nsys.path.append(str(WORKFLOWS_DIR))\nfrom tc_track_density import read_stitch_nodes_tracks\n"

        # also clear the output block where the error was printed so the user can re-run
        if "from tc_track_density import read_stitch_nodes_tracks" in "".join(source):
             if 'outputs' in cell:
                 cell['outputs'] = []

with open(notebook_path, "w") as f:
    json.dump(nb, f, indent=1)
    f.write("\n")

print("Fixed import in notebook.")
