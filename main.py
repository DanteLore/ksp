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


def save_to_sfs_file(data, filename):
    with open(filename, mode='w') as sfs_file:
        save_sfs_object(data, sfs_file)


def fix_docking_ports(vessel):
    print(f"Checking vessel named: {vessel['name']}")
    parts = vessel['PART']

    if not parts or len(parts) == 0 or not isinstance(parts, list):
        print("Could not find root part - probably a game-generated craft (e.g. rescue mission or asteroid)")
        return

    root = parts[0]
    docking_ports = {}

    print(f"Vessel Ref: {vessel['ref']} Root Part Name: {root['name']} Uid {root['uid']}")
    for part in parts:
        # Docking ports are just parts in the tree...
        if 'docking' in part['name']:
            docking_ports[part['uid']] = part

    if len(docking_ports) == 0:
        print("Vessel has no docking ports - all fine!")
        return
    print("Docking Ports:")
    for this_port_uid, this_docking_port in docking_ports.items():
        # The docking node module contains information on the part to which this part is docked.
        # If portA is docked to portB
        # portA.ModuleDockingNode.dockUId == portA.uid
        # and
        # portB.ModuleDockingNode.dockUId == portB.uid
        this_docking_node = docking_node_for(this_docking_port)

        # The DOCKEDVESSEL object just stores information to re-root the attached vessel when it splits back off.
        # e.g. Name, root ID, vessel type etc.
        # Seems a DOCKEDVESSEL object seems to appear on both sides in a healthy ship
        this_docked_vessel = this_docking_node.get('DOCKEDVESSEL')

        other_port_uid = this_docking_node['dockUId']
        other_port = docking_ports.get(other_port_uid)
        other_docking_node = docking_node_for(other_port) if other_port else None
        other_docked_vessel = other_docking_node.get('DOCKEDVESSEL') if other_docking_node else None

        if this_docking_node['state'] in ['Ready']:
            print(f"  Port UID {this_port_uid} is undocked with state {this_docking_node['state']}")

            if this_docked_vessel:
                print(f"    Found unused docked vessel info.  Deleting")
                this_docking_node.pop('DOCKEDVESSEL')

            if this_docking_node['dockUId'] != '0':
                print(f"    dockUId set for undocked port ({this_docking_node['dockUId']})")
                if not other_port:
                    print(f"    dockUid {this_docking_node['dockUId']} is not a part on this vessel - probably an undocked vessel")
                    print(f"    setting dockUid to zero, just for neatness")
                    this_docking_node['dockUId'] = 0
                else:
                    print(f"    dockUid {this_docking_node['dockUId']} is a part in this vessel!  Suss!")
                    if other_docking_node['dockUId'] == this_docking_port["uid"]:
                        if 'Docked' in other_docking_node['state']:
                            print(f"    Other docking node thinks it's docked to this part with state '{other_docking_node['state']}', so we're docked without knowing!")
                            new_state = "Docked (dockee)" if "docker" in other_docking_node['state'] else "Docked (docker)"
                            print(f"    Updating our state to {new_state}")
                            this_docking_node['state'] = new_state
                        else:
                            print(f"    Other docking port has state '{other_docking_node['state']}'")
        else:
            print(f"  Port UID {this_port_uid} is docked with state {this_docking_node['state']}")

            if this_docking_node['state'] in ['Docked (same vessel)', 'Disengage']:
                print(f"    Docking state '{this_docking_node['state']}' is dodgy.")
                if other_docking_node:
                    new_state = "Docked (dockee)" if "docker" in other_docking_node['state'] else "Docked (docker)"
                    print(f"    Changing state to {new_state} to match other port's state of {other_docking_node['state']}")
                    this_docking_node['state'] = new_state
                else:
                    print(f"    No docked port found on this vessel, so changing state to 'Ready'")
                    this_docking_node['state'] = 'Ready'


def docking_node_for(docking_port):
    docking_nodes = [n for n in docking_port['MODULE'] if n['name'] == 'ModuleDockingNode']
    if len(docking_nodes) > 0:
        return docking_nodes[0]
    else:
        return None


def main():
    save = parse_save_file(INPUT_FILENAME)

    vessels = [v for v in save['GAME']['FLIGHTSTATE']['VESSEL'] if v['type'] in PLAYER_VESSELS]
    # names = [f"{v['name']} : {v['type']}" for v in vessels]
    # print('\n'.join(names))

    for v in vessels:
        fix_docking_ports(v)

    with open(OUTPUT_JSON_FILENAME, mode='w') as f:
        f.write(json.dumps(save, indent=4))

    save_to_sfs_file(save, OUTPUT_SFS_FILENAME)

    print(f"Done!")


if __name__ == "__main__":
    main()

