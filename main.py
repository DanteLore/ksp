import re
import json

INPUT_FILENAME = "data/quicksave #119.sfs"
OUTPUT_JSON_FILENAME = "data/new.json"
OUTPUT_SFS_FILENAME = "data/new.sfs"
PROPERTY = r"\s*\w+\s=\s*\w*\s*"
OBJECT = r"\s*[A-Za-z0-9]+\s*"
CAREER_LOG = "CAREER_LOG"
PLAYER_VESSELS = ['Probe', 'Ship', 'Lander', 'Relay', 'Station', 'Plane', 'Base', 'Debris']


def do_parse_save_file(file, current, depth=0):
    while True:
        text = file.readline()

        if not text:
            return

        text = text.strip()

        if text == '}':
            return
        elif re.search(PROPERTY, text):
            name, value = [x.strip() for x in text.split('=', 1)]

            set_prop(current, name, value)
        elif re.search(OBJECT, text):
            child = {}
            set_prop(current, text, child)
            do_parse_save_file(file, child, depth + 1)


def set_prop(current, name, value):
    if name in current:
        if isinstance(current[name], list):
            current[name].append(value)
        else:
            current[name] = [current[name], value]
    else:
        current[name] = value


def parse_save_file(filename):
    with open(filename, encoding='utf-8') as f:
        root = {}
        do_parse_save_file(f, root)
        return root


def docking_port_info(vessel):
    parts = vessel['PART']
    root = parts[0]

    print(f"Vessel Name: {vessel['name']} Ref: {vessel['ref']} Root Part Name: {root['name']} Uid {root['uid']}")
    print("Docking Ports:")
    for part in parts:
        # Docking ports are just parts in the tree...
        if 'docking' in part['name']:
            print(f"  Port Name: {part['name']} uid: {part['uid']}")

            # The docking node module contains information on the part to which this part is docked.
            # If portA is docked to portB
            # portA.ModuleDockingNode.dockUId == portA.uid
            # and
            # portB.ModuleDockingNode.dockUId == portB.uid
            docking_node = [n for n in part['MODULE'] if n['name'] == 'ModuleDockingNode'][0]
            print(f"    Docking Node: State: {docking_node['state']} dockUId: {docking_node['dockUId']}")

            # The DOCKEDVESSEL object just stores information to re-root the attached vessel when it splits back off.
            # e.g. Name, root ID, vessel type etc.
            # Seems a DOCKEDVESSEL object seems to appear on both sides in a healthy ship
            if 'DOCKEDVESSEL' in docking_node:
                print("      Docked Vessel: " + str(docking_node['DOCKEDVESSEL']))


def save_sfs_object(obj, file, depth=0):
    for key in obj.keys():
        indent = '\t' * depth

        if isinstance(obj[key], dict):
            file.write(f"{indent}{key}\n")
            file.write(f"{indent}{{\n")
            save_sfs_object(obj[key], file, depth+1)
            file.write(f"{indent}}}\n")
        elif isinstance(obj[key], list):
            for item in obj[key]:
                if isinstance(item, dict):
                    file.write(f"{indent}{key}\n")
                    file.write(f"{indent}{{\n")
                    save_sfs_object(item, file, depth+1)
                    file.write(f"{indent}}}\n")
                else:
                    file.write(f"{indent}{key} = {str(item)}\n")
        else:
            file.write(f"{indent}{key} = {obj[key]}\n")

        print(key)


def save_to_sfs_file(data, filename):
    with open(filename, mode='w') as sfs_file:
        save_sfs_object(data, sfs_file)


def main():
    save = parse_save_file(INPUT_FILENAME)

    with open(OUTPUT_JSON_FILENAME, mode='w') as f:
        f.write(json.dumps(save, indent=4))

    save_to_sfs_file(save, OUTPUT_SFS_FILENAME)

    vessels = [v for v in save['GAME']['FLIGHTSTATE']['VESSEL'] if v['type'] in PLAYER_VESSELS]
    # names = [f"{v['name']} : {v['type']}" for v in vessels]
    # print('\n'.join(names))

    vessel_name = 'Go Everywhere 1.0'
    vessel_name = 'Kerbin Station'
    v = [v for v in vessels if v['name'] == vessel_name][0]
    docking_port_info(v)

    print(f"Done!")


if __name__ == "__main__":
    main()

