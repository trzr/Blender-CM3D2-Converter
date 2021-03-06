# 画面上部 (「情報」エリア → ヘッダー) → ヘルプ
import os
import re
import sys
import urllib.request
import zipfile
import subprocess
import datetime
import xml.sax.saxutils
import addon_utils
import bpy
from . import common
from . import compat


# メニュー等に項目追加
def menu_func(self, context):
    icon_id = common.kiss_icon()
    self.layout.separator()
    self.layout.operator('script.update_cm3d2_converter', icon_value=icon_id)
    self.layout.operator('wm.call_menu', icon_value=icon_id, text="CM3D2 Converterの更新履歴").name = 'INFO_MT_help_CM3D2_Converter_RSS'
    self.layout.operator('wm.show_cm3d2_converter_preference', icon_value=icon_id)


# 更新履歴メニュー
@compat.BlRegister()
class INFO_MT_help_CM3D2_Converter_RSS(bpy.types.Menu):
    bl_idname = 'INFO_MT_help_CM3D2_Converter_RSS'
    bl_label = "CM3D2 Converterの更新履歴"

    def draw(self, context):
        try:
            response = urllib.request.urlopen(common.URL_ATOM)
            html = response.read().decode('utf-8')
            titles = re.findall(r'\<title\>[　\s]*([^　\s][^\<]*[^　\s])[　\s]*\<\/title\>', html)[1:]
            updates = re.findall(r'\<updated\>([^\<\>]*)\<\/updated\>', html)[1:]
            links = re.findall(r'<link [^\<\>]*href="([^"]+)"/>', html)[2:]
            version_datetime = datetime.datetime.strptime(str(common.bl_info["version"][0]) + "," + str(common.bl_info["version"][1]) + "," + str(common.bl_info["version"][2]) + "," + str(common.bl_info["version"][3]) + "," + str(common.bl_info["version"][4]) + "," + str(common.bl_info["version"][5]), '%Y,%m,%d,%H,%M,%S')

            output_data = []
            update_diffs = []
            for title, update, link in zip(titles, updates, links):
                title = xml.sax.saxutils.unescape(title, {'&quot;': '"'})

                rss_datetime = datetime.datetime.strptime(update, '%Y-%m-%dT%H:%M:%SZ') + datetime.timedelta(hours=9)
                diff_seconds = datetime.datetime.now() - rss_datetime
                icon = 'SORTTIME'
                if 60 * 60 * 24 * 7 < diff_seconds.total_seconds():
                    icon = 'NLA'
                elif 60 * 60 * 24 * 3 < diff_seconds.total_seconds():
                    icon = 'COLLAPSEMENU'
                elif 60 * 60 * 24 < diff_seconds.total_seconds():
                    icon = 'TIME'
                elif 60 * 60 < diff_seconds.total_seconds():
                    icon = 'RECOVER_LAST'
                else:
                    icon = 'PREVIEW_RANGE'

                if 60 * 60 * 24 <= diff_seconds.total_seconds():
                    date_str = "%d日前" % int(diff_seconds.total_seconds() / 60 / 60 / 24)
                elif 60 * 60 <= diff_seconds.total_seconds():
                    date_str = "%d時間前" % int(diff_seconds.total_seconds() / 60 / 60)
                elif 60 <= diff_seconds.total_seconds():
                    date_str = "%d分前" % int(diff_seconds.total_seconds() / 60)
                else:
                    date_str = "%d秒前" % diff_seconds.total_seconds()

                text = "(" + date_str + ") " + title

                update_diff = abs((version_datetime - rss_datetime).total_seconds())

                output_data.append((text, icon, link, update_diff))
                update_diffs.append(update_diff)

            min_update_diff = sorted(update_diffs)[0]
            for text, icon, link, update_diff in output_data:

                if update_diff == min_update_diff:
                    if update_diff < 30:
                        text = "Now! " + text
                    icon = 'QUESTION'

                self.layout.operator('wm.url_open', text=text, icon=icon).url = link
        except:
            self.layout.label(text="更新の取得に失敗しました", icon='ERROR')


@compat.BlRegister()
class CNV_OT_update_cm3d2_converter(bpy.types.Operator):
    bl_idname = 'script.update_cm3d2_converter'
    bl_label = "CM3D2 Converterを更新"
    bl_description = "GitHubから最新版のCM3D2 Converterアドオンをダウンロードし上書き更新します"
    bl_options = {'REGISTER'}

    is_restart = bpy.props.BoolProperty(name="更新後にBlenderを再起動", default=True)
    is_toggle_console = bpy.props.BoolProperty(name="再起動後にコンソールを閉じる", default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.menu('INFO_MT_help_CM3D2_Converter_RSS', icon='INFO')
        self.layout.prop(self, 'is_restart', icon='BLENDER')
        self.layout.prop(self, 'is_toggle_console', icon='CONSOLE')

    def execute(self, context):

        zip_path = os.path.join(bpy.app.tempdir, "Blender-CM3D2-Converter-" + common.BRANCH + ".zip")
        addon_path = os.path.dirname(__file__)

        response = urllib.request.urlopen(common.URL_MODULE)
        zip_file = open(zip_path, 'wb')
        zip_file.write(response.read())
        zip_file.close()

        zip_file = zipfile.ZipFile(zip_path, 'r')
        for path in zip_file.namelist():
            if not os.path.basename(path):
                continue
            sub_dir = os.path.split(os.path.split(path)[0])[1]
            if sub_dir == "CM3D2 Converter":
                file = open(os.path.join(addon_path, os.path.basename(path)), 'wb')
                file.write(zip_file.read(path))
                file.close()
        zip_file.close()

        if self.is_restart:
            filepath = bpy.data.filepath
            command_line = [sys.argv[0]]
            if filepath:
                command_line.append(filepath)
            if self.is_toggle_console:
                py = os.path.join(os.path.dirname(__file__), "console_toggle.py")
                command_line.append('-P')
                command_line.append(py)

            subprocess.Popen(command_line)
            bpy.ops.wm.quit_blender()
        else:
            self.report(type={'INFO'}, message="Blender-CM3D2-Converterを更新しました、再起動して下さい")
        return {'FINISHED'}


@compat.BlRegister()
class CNV_OT_show_cm3d2_converter_preference(bpy.types.Operator):
    bl_idname = 'wm.show_cm3d2_converter_preference'
    bl_label = "CM3D2 Converterの設定画面を開く"
    bl_description = "CM3D2 Converterアドオンの設定画面を表示します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        my_info = None
        for module in addon_utils.modules():
            info = addon_utils.module_bl_info(module)
            if info['name'] == common.ADDON_NAME:
                my_info = info
                break
        area = common.get_request_area(context, compat.pref_type())
        if area and my_info:
            compat.get_prefs(context).active_section = 'ADDONS'
            context.window_manager.addon_search = my_info['name']
            context.window_manager.addon_filter = 'All'
            if 'COMMUNITY' not in context.window_manager.addon_support:
                context.window_manager.addon_support = {'OFFICIAL', 'COMMUNITY'}
            if not my_info['show_expanded']:
                if compat.IS_LEGACY:
                    bpy.ops.wm.addon_expand(module=__package__)
                else:
                    bpy.ops.preferences.addon_expand(module=__package__)
        else:
            self.report(type={'ERROR'}, message="表示できるエリアが見つかりませんでした")
            return {'CANCELLED'}
        return {'FINISHED'}
