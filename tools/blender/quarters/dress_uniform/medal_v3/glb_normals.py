"""Keep source GLB normals through Blender's packed custom-normal round trip."""
import json
import struct
import numpy as np


def preserve_normals(source,destination):
    def load(path):
        blob=path.read_bytes()
        size=struct.unpack_from('<I',blob,12)[0]
        return json.loads(blob[20:20+size]),bytearray(blob[28+size:])
    def accessor(doc,binary,index,n):
        a=doc['accessors'][index]
        view=doc['bufferViews'][a['bufferView']]
        dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']])
        return np.ndarray((a['count'],n),dtype=dtype,buffer=binary,
            offset=view.get('byteOffset',0)+a.get('byteOffset',0),
            strides=(view.get('byteStride',n*dtype.itemsize),dtype.itemsize))
    original,source_binary=load(source)
    baked,baked_binary=load(destination)
    source_meshes={n['name'].split('_')[0]:original['meshes'][n['mesh']]
                   for n in original['nodes'] if 'mesh' in n}
    changes={}
    for node in baked['nodes']:
        if 'mesh' not in node:
            continue
        part=node['name'].split('_')[0]
        old=source_meshes[part]['primitives'][0]
        new=baked['meshes'][node['mesh']]['primitives'][0]
        old_index=accessor(original,source_binary,old['indices'],1).ravel()
        new_index=accessor(baked,baked_binary,new['indices'],1).ravel()
        old_normal=accessor(original,source_binary,old['attributes']['NORMAL'],3)
        new_normal=accessor(baked,baked_binary,new['attributes']['NORMAL'],3)
        before=new_normal.copy()
        restored=np.empty_like(new_normal)
        restored[new_index]=old_normal[old_index]
        assert np.array_equal(restored[new_index],old_normal[old_index])
        new_normal[:]=restored
        changes[part]={'restored_normal_components':int(np.count_nonzero(before!=new_normal)),
                       'packed_roundtrip_max_component_difference':float(np.max(abs(before-new_normal)))}
    payload=json.dumps(baked,separators=(',',':')).encode()
    payload+=b' '*((-len(payload))%4)
    binary=bytes(baked_binary)
    binary+=b'\0'*((-len(binary))%4)
    total=12+8+len(payload)+8+len(binary)
    destination.write_bytes(struct.pack('<III',0x46546c67,2,total)
        +struct.pack('<II',len(payload),0x4e4f534a)+payload
        +struct.pack('<II',len(binary),0x004e4942)+binary)
    return changes


if __name__=='__main__':
    from pathlib import Path
    folder=Path(__file__).resolve().parents[5]/'tmp/issue130-v3/fit1'
    changes=preserve_normals(folder/'medal-low.glb',folder/'medal-low-normalmapped.glb')
    (folder/'normal-export-roundtrip.json').write_text(json.dumps(changes,indent=2))
    print(json.dumps(changes,indent=2))
