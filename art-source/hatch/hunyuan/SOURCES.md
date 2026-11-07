# Generated frame sources

**Territory restriction: the Tencent Hunyuan 3D 2.0 Community License excludes the European Union, United Kingdom and South Korea. Section 5.c also restricts use, distribution and display of outputs outside that Territory. These files must not be pushed or shipped as unrestricted worldwide assets.** This local source freeze does not resolve distribution permission.

`C-s410-sv.glb` is the driver's chosen frame. `C-s412-sv.glb` is the recorded alternative. Both are machine-generated Hunyuan3D-2mv outputs, not approved production meshes. Raw bytes are unchanged. `provenance.json` records hashes, exact inputs, alpha mask, FLUX input-edit prompt, seeds, model revision, checkpoint checksum, configuration, and the generator source snapshot. The original `C-front.metadata.json` contains literal `null`; the frozen generation recipe supplies the FLUX command and settings, rather than that metadata file. No Hunyuan Paint output is used.

`LICENSE` is the unmodified licence text fetched from https://huggingface.co/tencent/Hunyuan3D-2/resolve/main/LICENSE. `Notice` carries its required attribution. The input image was produced with FLUX.2-klein-4B; that model's Apache-2.0 terms do not replace the Hunyuan output restrictions.

The prototype directory has no Git metadata and did not log a generator commit. The frozen `generate.py` and all shape-generation modules match published revision `f26094cde48344b3165d67271cc98ad99610abf8` byte-for-byte. The unused paint pipeline differs; its actual bytes are retained too. This establishes the shape code's reproducible identity, not a claim that the prototype logged that revision at generation time.

`baseline-physical.json` was exported before fitting-code changes from GONE `c2a0157`, using `godot --headless --path . -s tools/export_hatch_parts.gd`. It independently pins both signs' existing physical records. The selection files index the exact raw topology, declare only exact zero-area removals, and preserve all positive-area faces in the source fixture. Hardware separation and bounded fitting must be recorded before a production candidate is built.
