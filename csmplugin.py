# Authored by: Common Sense Machines, Inc.

import requests
import pprint
import bpy
import requests
import time
import os
import sys
import tempfile
from pathlib import Path

from bpy.props import (StringProperty,
                       PointerProperty,
                       )
                       
from bpy.types import (Panel,
                       PropertyGroup,
                       )

CSM_EMAIL = ''
CSM_PASSWORD = ''
bpy.types.Scene.CSM_API_TOKEN = ''

bl_info = {
    "name": "CSM Bot",
    "blender": (3, 30, 0),
    "category": "Object",
}
# ------------------------------------------------------------------------
#    Server
# ------------------------------------------------------------------------
def login(email, password):
    response = requests.post(
        "https://devapi.csm.ai:3001/user/login",
        headers={
          "accept": "application/json",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
          "email": email,
          "password": password
        },
        verify=False,
    )
    print(response.json())
    return response.json()

def download_csm_asset(api_token, session_id):
    response = requests.get(
        f"https://devapi.csm.ai:3001/session/{session_id}",
        headers={
          "accept": "application/json",
          "Authorization": f"Bearer {api_token}",
        },
        verify=False,
    )
    print(response.json())
    return response.json()
    
    
# ------------------------------------------------------------------------
#    CSM code generation api 
# ------------------------------------------------------------------------

class CSMCodegenServer():
    def __init__(
        self,
        login,
        password,
        verbose=False,
    ):

      self.server_url = 'coderapi.csm.ai'
      self.verbose = verbose
      self.headers = {
          "username": login,
          "api-secret-key": password,
          "Content-Type": "application/json"
      }

    def ping(self, message='hello world'):
        response = requests.post(f"https://{self.server_url}/csm_coder/ping",
                                 headers=self.headers,
                                 json={'message': message})
        if self.verbose:
            print('/ping response: ' + response.text)
        return response

    def codegen(self, prompt):
        if prompt == '':
            return ''
        response = requests.post(
            f"https://{self.server_url}/csm_coder/codegen",
            headers=self.headers,
            json={
                'prompt': prompt,
                'model': 'blender-python'
            })
        if self.verbose:
            print('/ping response: ' + response.text)
        return response

# ------------------------------------------------------------------------
#    Execute code generated from APIs 
# ------------------------------------------------------------------------

def codegen(prompt):
    global CSM_EMAIL, CSM_PASSWORD
    if CSM_EMAIL == '' or CSM_PASSWORD == '':
        ShowMessageBox('Please login using your CSM credentials!')
        return

    print('\n\nCalling CSM API.')

    csm_server_handle = CSMCodegenServer(
        login=CSM_EMAIL, 
        password=CSM_PASSWORD, 
        verbose=True)   
    
    LAST_PROMPT = prompt
    if prompt == '':
      ShowMessageBox('Prompt cannot be empty!')
      return
    try:
      dynamic_func = csm_server_handle.codegen(prompt=prompt).json()['prediction']['code']
    except:
      ShowMessageBox('Error connecting to the server.')
      return
    ShowMessageBox(dynamic_func)
    print('Synthesized Code:')
    print('------------------------')
    print(dynamic_func)
    print('-------- result --------')
    exec(dynamic_func)
    
    # add snippet to codegen file for reference
    codeblock = bpy.data.texts.new('csmcoder')
    codeblock.write(f'# prompt: {prompt}\n')
    codeblock.write(f'# time: {time.time()}\n')
    codeblock.write(dynamic_func + '\n\n\n')

  
# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

def ShowMessageBox(message = "", title = "Synthesized Code", icon = 'INFO'):
    def draw(self, context):
        for n in message.split('\n'):
            self.layout.label(text=n)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


class MyProperties(PropertyGroup):

    def __init__(self):
      super(PropertyGroup, self).__init__()

    text: StringProperty(
        name="Text",
        description=":",
        default="",
        maxlen=512
        )

    email: StringProperty(
        name="Email",
        description=":",
        default="",
        maxlen=512,
        #update=csm_login
        )
        
    password: StringProperty(
        name="Password",
        description=":",
        default="",
        maxlen=512
        )

    session_name: StringProperty(
        name="Web ID",
        description=":",
        default="",
        maxlen=512,
        #update=csm_session_init
        )
        
        
# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

# ------------------------------------------------------------------------
#    Download CSM Assets
# ------------------------------------------------------------------------

class CodeOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "scene.code_operator"
    bl_label = "Text-to-Code Generation"
    bl_context = "objectmode"
    bl_options = {"INTERNAL"}
    bl_category = "CSM Bot"
    option : bpy.props.StringProperty(name='option')

    def execute(self, context):
        session_name = context.scene.session_name.session_name
        api_token = bpy.types.Scene.CSM_API_TOKEN
        codegen(prompt = context.scene.text.text)
        return {'FINISHED'}

class CodePanel(bpy.types.Panel):
    bl_label = "Text-to-Code Generation"
    bl_idname = "SCENE_PT_code"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "CSM Bot"

    def op(self, layout, value):
        layout.operator("scene.code_operator", text=value).option=value

    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene.text, "text")
            
        col = layout.column(align=True)
        row = col.row(align=True)
        self.op(row, "Generate Code")
    
    
# ------------------------------------------------------------------------
#    Download CSM Assets
# ------------------------------------------------------------------------

class SessionOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "scene.csmasset_operator"
    bl_label = "CSM Asset Operator"
    bl_context = "objectmode"
    bl_options = {"INTERNAL"}
    bl_category = "CSM Bot"
    option : bpy.props.StringProperty(name='option')

    def execute(self, context):
        session_name = context.scene.session_name.session_name
        api_token = bpy.types.Scene.CSM_API_TOKEN
        obj_type = context.scene.obj_type
        obj_type_msg = 'Fast NeRF' if obj_type == 0 else 'Slow NeRF'
        ShowMessageBox(f'Downloading {obj_type_msg}', title='Authentication Error', icon='ERROR')
        if api_token == '':
            ShowMessageBox("CSM API token cannot be empty. Please login.", title='Authentication Error', icon='ERROR')
        else:
            res = download_csm_asset(api_token, session_name)
            if res['statusCode'] == 200:
                ShowMessageBox('Downloading...', title='Session Status', icon='INFO')
                if 'slowinvg_mesh_obj_urls' not in res['data']:
                    ShowMessageBox('Mesh generation not done.', title='Session Status', icon='ERROR')
                    return
                if obj_type == 1:
                    mesh_urls = res['data']['slowinvg_mesh_obj_urls']
                else:
                    mesh_urls = res['data']['fastinvg_mesh_obj_urls']
                dst_dir = f'{os.path.expanduser("~")}/csm_blender_plugin/{session_name}'
                os.system(f'mkdir -p {dst_dir}')
                obj_fname = ''
                for url in mesh_urls:
                    filter = '/fastinvg_textured_mesh/' if obj_type == '0' else '/slowinvg_textured_mesh/'
                    fname = url.split(filter)[-1].split('?')[0]
                    dst = f'{dst_dir}/{fname}'
                    if not os.path.exists(dst):
                        os.system(f'wget -O {dst} \"{url}\"')
                    if '.obj' in fname:
                        obj_fname = dst
                    print(f'Downloading to: {dst}')
                # load object into the bpy scene
                if 'Foreground' not in bpy.data.collections:
                    foreground_collection = bpy.data.collections.new('Foreground')
                    bpy.context.scene.collection.children.link(foreground_collection)
                bpy.ops.import_scene.obj(filepath=obj_fname)
                bpy.data.collections["Foreground"].objects.link(bpy.context.selected_objects[0])
            else:
                ShowMessageBox(res['message'], title='Session Status', icon='INFO')
            

        return {'FINISHED'}

class SessionPanel(bpy.types.Panel):
    bl_label = "Download CSM Session"
    bl_idname = "SCENE_PT_session"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "CSM Bot"

    # This is how you make a static enum prop for the scene
    enum_items = (('0','Fast NeRF',''),('1','Slow NeRF',''))
    bpy.types.Scene.obj_type = bpy.props.EnumProperty(items = enum_items)

    def op(self, layout, value):
        layout.operator("scene.csmasset_operator", text=value).option=value

    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene.session_name, "session_name")
            
        layout.label(text="Select Asset Type")
        layout.prop(context.scene, 'obj_type', expand=True)

        col = layout.column(align=True)
        row = col.row(align=True)
        self.op(row, "Download")
    
# ------------------------------------------------------------------------
#    CSM Login
# ------------------------------------------------------------------------


class LoginOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "scene.login_operator"
    bl_label = "Login Operator"
    bl_context = "objectmode"
    bl_options = {"INTERNAL"}
    bl_category = "CSM Bot"
    option : bpy.props.StringProperty(name='option')

    def execute(self, context):
        email = context.scene.email.email
        password = context.scene.password.password
        if email == '' or password == '':
            ShowMessageBox("Email and password cannot be empty.", title='Login Error', icon='ERROR')
        else:
            res = login(email, password)
            ShowMessageBox(res['message'], title='Login Status', icon='ERROR')
            if res['statusCode'] == 200:
                bpy.types.Scene.CSM_API_TOKEN = res['data']['token']
                global CSM_EMAIL, CSM_PASSWORD
                CSM_EMAIL = email
                CSM_PASSWORD = password
                # clear login info for sanctity
                context.scene.email.email = ''
                context.scene.password.password = ''
        return {'FINISHED'}

class LoginPanel(bpy.types.Panel):
    bl_label = "CSM Login (csm.ai/dashboard)"
    bl_idname = "SCENE_PT_login"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "CSM Bot"

    def op(self, layout, value):
        layout.operator("scene.login_operator", text=value).option=value

    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene.email, "email")
        layout.prop(context.scene.password, "password")
            
        col = layout.column(align=True)
        row = col.row(align=True)
        self.op(row, "Login")
        
# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    MyProperties,
    CodePanel,
    CodeOperator,
    SessionPanel,
    SessionOperator,
    LoginPanel,
    LoginOperator
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.text = PointerProperty(type=MyProperties)
    bpy.types.Scene.email = PointerProperty(type=MyProperties)
    bpy.types.Scene.password = PointerProperty(type=MyProperties)
    bpy.types.Scene.session_name = PointerProperty(type=MyProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.text
    del bpy.types.Scene.email
    del bpy.types.Scene.password
    del bpy.types.Scene.session_name



def install_addons():
    global BASEDIR
    path_to_script_dir = f'{str(Path.home())}/blender_addons'
    os.system(f'mkdir {path_to_script_dir}')
    # install relevant plugins before proceeding
    
    if not os.path.exists(f'{path_to_script_dir}/v2.0.0.zip'):
        os.system(f'cd {path_to_script_dir} && wget https://github.com/BrendanParmer/NodeToPython/archive/refs/tags/v2.0.0.zip')
    if not os.path.exists(f'{path_to_script_dir}/sverchok-1_1_0.zip'):
        os.system(f'cd {path_to_script_dir} && wget https://github.com/nortikin/sverchok/releases/download/v1.1.0/sverchok-1_1_0.zip')
        os.system(f'cd {path_to_script_dir} && cp sverchok-1_1_0.zip sverchok-master.zip')
    if not os.path.exists(f'{path_to_script_dir}/drop_it_v1.2.zip'):
        os.system(f'cd {path_to_script_dir} && wget https://storage.googleapis.com/3d-model-library/drop_it_v1.2.zip')
    if not os.path.exists(f'{path_to_script_dir}/building_tools-v1.0.9.zip'):
        os.system(f'cd {path_to_script_dir} && wget https://github.com/ranjian0/building_tools/releases/download/v1.0.9/building_tools-v1.0.9.zip')
    if not os.path.exists(f'{path_to_script_dir}/add_mesh_SpaceshipGenerator-v1.6.5.zip'):
        os.system(f'cd {path_to_script_dir} && wget https://github.com/ldo/blender_spaceship_generator/releases/download/v1.6.5/add_mesh_SpaceshipGenerator-v1.6.5.zip')
    if not os.path.exists(f'{path_to_script_dir}/projectile.zip'):
        os.system(f'cd {path_to_script_dir} && wget https://github.com/natecraddock/projectile/releases/download/v2.1/projectile.zip')
    if not os.path.exists(f'{path_to_script_dir}/tree-gen-0.0.4.zip'):
        os.system(f'cd {path_to_script_dir} && wget https://github.com/friggog/tree-gen/releases/download/v0.0.4/tree-gen-0.0.4.zip')
    if not os.path.exists(f'{path_to_script_dir}/geometry_script.zip'):
        os.system(f'cd {path_to_script_dir} && wget https://github.com/carson-katri/geometry-script/releases/download/0.1.2/geometry_script.zip')

    #Define a list of the files in this folder, i.e. directory. The method listdir() will return this list from our folder of downloaded scripts. 
    file_list = sorted(os.listdir(path_to_script_dir))

    #Further specificy that of this list of files, you only want the ones with the .zip extension.
    script_list = [item for item in file_list if item.endswith('.zip')]
    
    #Specify the file path of the individual scripts (their names joined with the location of your downloaded scripts folder) then use wm.addon_install() to install them. 
    for file in file_list:
        path_to_file = os.path.join(path_to_script_dir, file)
        bpy.ops.preferences.addon_install(overwrite=True, target='DEFAULT', filepath=path_to_file, filter_folder=True, filter_python=False, filter_glob="*.py;*.zip")

    #Specify which add-ons you want enabled. For example, Crowd Render, Pie Menu Editor, etc. Use the script's python module. 
    enableTheseAddons = ['geometry_script', 'tree-gen', 'projectile', 'node_to_python', 'sverchok-master', 'interactivetoolsblender-master', 'drop_it', 'building_tools', 'add_mesh_SpaceshipGenerator', 'camera_shakify-master'] 
    #Use addon_enable() to enable them.
    for string in enableTheseAddons: 
        name = enableTheseAddons
        try:
            bpy.ops.preferences.addon_enable(module = string)
        except:
            pass
        
if __name__ == "__main__":
    install_addons()
    register()