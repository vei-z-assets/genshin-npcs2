import bpy
import os
import zipfile
import tempfile

# --- CONFIGURATION ---
TARGET_DIR = r"C:\Users\veizou\vei-z\public\content\genshin\npc2"
# ---------------------

def fix_materials_with_diffuse(search_folder):
    """Finds _Diffuse textures (ignoring _Diffuse_A and _Lightmap) and links them to materials."""
    diffuse_textures = {}
    for root, dirs, files in os.walk(search_folder):
        for file in files:
            lower_name = file.lower()
            if lower_name.endswith((".png", ".tga", ".jpg", ".dds")):
                if "diffuse" in lower_name and "diffuse_a" not in lower_name:
                    diffuse_textures[lower_name] = os.path.join(root, file)

    if not diffuse_textures:
        return

    for mat in bpy.data.materials:
        if not mat.use_nodes:
            mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        output = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0.85

        clean_mat_name = mat.name.lower().split(".")[0]
        matched_tex_path = None

        for part in reversed(clean_mat_name.split("_")):
            if len(part) > 2:
                for tex_name, tex_path in diffuse_textures.items():
                    if part in tex_name:
                        matched_tex_path = tex_path
                        break
            if matched_tex_path:
                break

        if not matched_tex_path:
            matched_tex_path = list(diffuse_textures.values())[0]

        if matched_tex_path:
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.image = bpy.data.images.load(matched_tex_path)
            links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])

def convert_fbx_list(fbx_files, search_folder, out_folder, folder_name):
    total_fbx = len(fbx_files)
    for index, fbx_path in enumerate(fbx_files, start=1):
        glb_name = str(index) if total_fbx > 1 else folder_name
        glb_path = os.path.join(out_folder, f"{glb_name}.glb")

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        fix_materials_with_diffuse(search_folder)
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')

def process_in_place():
    # Walks through every subfolder inside TARGET_DIR regardless of depth
    for root, dirs, files in os.walk(TARGET_DIR):
        folder_name = os.path.basename(root)

        fbx_files = [os.path.join(root, f) for f in sorted(files) if f.lower().endswith(".fbx")]
        zip_files = [f for f in files if f.lower().endswith(".zip")]

        if fbx_files:
            convert_fbx_list(fbx_files, root, root, folder_name)
            print(f"Updated in place (from loose files): {folder_name}")
        elif zip_files:
            zip_path = os.path.join(root, zip_files[0])
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    zipf.extractall(temp_dir)

                zip_fbx = []
                for z_root, z_dirs, z_files in os.walk(temp_dir):
                    for file in sorted(z_files):
                        if file.lower().endswith(".fbx"):
                            zip_fbx.append(os.path.join(z_root, file))

                if zip_fbx:
                    convert_fbx_list(zip_fbx, temp_dir, root, folder_name)
                    print(f"Updated in place (from ZIP): {folder_name}")

if __name__ == "__main__":
    process_in_place()
