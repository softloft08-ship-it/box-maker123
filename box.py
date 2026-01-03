import sys
import requests  # Required for the updater: pip install requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QPushButton, 
                             QWidget, QFileDialog, QLineEdit, QHBoxLayout, QLabel, 
                             QScrollArea, QListWidget, QColorDialog, QCheckBox, 
                             QSpinBox, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image, ImageDraw, ImageFont

class BoxRenderer(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.texture_id = None
        self.bg_texture_id = None
        self.y_rot, self.x_rot, self.zoom = -25, 15, -16
        self.last_pos = QPoint()
        self.box_color = (255, 255, 255, 255)
        self.img_path = None
        self.text_layers = [] 
        self.icons = [] 
        self.dragging_item = None
        self.drag_mode = False 
        self.needs_texture_update = True

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        self.update_master_texture()

    def update_master_texture(self):
        self.makeCurrent()
        master = Image.new("RGBA", (2048, 1024), self.box_color)
        draw = ImageDraw.Draw(master)
        if self.img_path:
            try:
                art = Image.open(self.img_path).convert("RGBA")
                art = art.resize((1024, 1024), Image.Resampling.LANCZOS)
                master.paste(art, (0, 0), art)
            except: pass
        for layer in self.text_layers:
            try:
                font = ImageFont.truetype(layer.get('font', "arial.ttf"), layer['size'])
                txt = layer['text']
                bbox = draw.textbbox((layer['x'], layer['y']), txt, font=font)
                layer['rect'] = QRect(int(bbox[0]), int(bbox[1]), int(bbox[2]-bbox[0]), int(bbox[3]-bbox[1]))
                draw.text((layer['x'], layer['y']), txt, font=font, fill=layer.get('color', (0,0,0,255)))
            except: pass
        for icon in self.icons:
            try:
                ic_img = Image.open(icon['path']).convert("RGBA")
                ic_img.thumbnail((icon['w'], icon['h']))
                master.paste(ic_img, (icon['x'], icon['y']), ic_img)
                icon['rect'] = QRect(icon['x'], icon['y'], icon['w'], icon['h'])
            except: pass
        img_data = master.transpose(Image.FLIP_TOP_BOTTOM).tobytes()
        if not self.texture_id: self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 2048, 1024, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        self.needs_texture_update = False

    def draw_bevel_box(self, width, height, depth, r):
        w, h, d = width - r, height - r, depth - r
        quad = gluNewQuadric()
        gluQuadricTexture(quad, GL_TRUE)
        glColor4ub(*self.box_color)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        # Main Faces
        glBegin(GL_QUADS)
        glNormal3f(0,0,1); glTexCoord2f(0,0); glVertex3f(-w,-h, depth); glTexCoord2f(0.5,0); glVertex3f(w,-h, depth); glTexCoord2f(0.5,1); glVertex3f(w,h, depth); glTexCoord2f(0,1); glVertex3f(-w,h, depth)
        glNormal3f(0,0,-1); glTexCoord2f(0.5,0); glVertex3f(w,-h,-depth); glTexCoord2f(0.6,0); glVertex3f(-w,-h,-depth); glTexCoord2f(0.6,1); glVertex3f(-w,h,-depth); glTexCoord2f(0.5,1); glVertex3f(w,h,-depth)
        glNormal3f(-1,0,0); glTexCoord2f(0.5,0); glVertex3f(-width,-h,-d); glTexCoord2f(0.6,0); glVertex3f(-width,-h,d); glTexCoord2f(0.6,1); glVertex3f(-width,h,d); glTexCoord2f(0.5,1); glVertex3f(-width,h,-d)
        glNormal3f(1,0,0);  glTexCoord2f(0.5,0); glVertex3f(width,-h,d); glTexCoord2f(0.6,0); glVertex3f(width,-h,-depth); glTexCoord2f(0.6,1); glVertex3f(width,h,-depth); glTexCoord2f(0.5,1); glVertex3f(width,h,d)
        glNormal3f(0,1,0);  glTexCoord2f(0.5,0); glVertex3f(-w,height,d); glTexCoord2f(0.6,0); glVertex3f(w,height,d); glTexCoord2f(0.6,1); glVertex3f(w,height,-d); glTexCoord2f(0.5,1); glVertex3f(-w,height,-d)
        glNormal3f(0,-1,0); glTexCoord2f(0.5,0); glVertex3f(-w,-height,-d); glTexCoord2f(0.6,0); glVertex3f(w,-height,-d); glTexCoord2f(0.6,1); glVertex3f(w,-height,d); glTexCoord2f(0.5,1); glVertex3f(-w,-height,d)
        glEnd()

        # Rounded Edges (UVs wrapped from texture)
        for x, y in [(w, h), (-w, h), (w, -h), (-w, -h)]:
            glPushMatrix(); glTranslatef(x, y, -d); gluCylinder(quad, r, r, 2*d, 32, 1); glPopMatrix()
        for y, z in [(h, d), (-h, d), (h, -d), (-h, -d)]:
            glPushMatrix(); glTranslatef(-w, y, z); glRotatef(90, 0, 1, 0); gluCylinder(quad, r, r, 2*w, 32, 1); glPopMatrix()
        for x, z in [(w, d), (-w, d), (w, -d), (-w, -d)]:
            glPushMatrix(); glTranslatef(x, -h, z); glRotatef(-90, 1, 0, 0); gluCylinder(quad, r, r, 2*h, 32, 1); glPopMatrix()
        
        # Rounded Corners
        for x in [-w, w]:
            for y in [-h, h]:
                for z in [-d, d]:
                    glPushMatrix(); glTranslatef(x, y, z); gluSphere(quad, r, 16, 16); glPopMatrix()
        gluDeleteQuadric(quad)

    def paintGL(self):
        if self.needs_texture_update: self.update_master_texture()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if self.bg_texture_id:
            glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING)
            glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); glOrtho(0,1,0,1,-1,1)
            glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
            glBindTexture(GL_TEXTURE_2D, self.bg_texture_id)
            glBegin(GL_QUADS); glTexCoord2f(0,0); glVertex2f(0,0); glTexCoord2f(1,0); glVertex2f(1,0); glTexCoord2f(1,1); glVertex2f(1,1); glTexCoord2f(0,1); glVertex2f(0,1); glEnd()
            glMatrixMode(GL_MODELVIEW); glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45, self.width()/self.height(), 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity(); glTranslatef(0, 0, self.zoom); glRotatef(self.x_rot, 1, 0, 0); glRotatef(self.y_rot, 0, 1, 0)
        self.draw_bevel_box(2.0, 3.5, 0.8, 0.05)

    def get_tex_coords(self, pos):
        w, h = self.width(), self.height()
        return int((pos.x() / w) * 1024), int((pos.y() / h) * 1024)

    def mousePressEvent(self, e):
        if self.drag_mode:
            tx, ty = self.get_tex_coords(e.position())
            for l in reversed(self.text_layers):
                if 'rect' in l and l['rect'].contains(tx, ty): self.dragging_item = l; return
            for i in reversed(self.icons):
                if 'rect' in i and i['rect'].contains(tx, ty): self.dragging_item = i; return
        self.last_pos = e.pos()

    def mouseMoveEvent(self, e):
        if self.drag_mode and self.dragging_item:
            tx, ty = self.get_tex_coords(e.position())
            self.dragging_item['x'] = tx - (self.dragging_item['rect'].width() // 2)
            self.dragging_item['y'] = ty - (self.dragging_item['rect'].height() // 2)
            self.needs_texture_update = True; self.update()
        elif not self.drag_mode:
            dx, dy = (e.position().x()-self.last_pos.x())*0.5, (e.position().y()-self.last_pos.y())*0.5
            if e.buttons() & Qt.MouseButton.LeftButton: self.x_rot += dy; self.y_rot += dx; self.update()
        self.last_pos = e.pos()

class MainWindow(QMainWindow):
    # --- UPDATE SYSTEM SETTINGS ---
    VERSION = "1.0"
    # Follow Step 2 below to replace these URLs with your own GitHub RAW links
    VERSION_URL = "https://github.com/softloft08-ship-it/box-maker123/blob/main/version.txt"
    UPDATE_URL = "https://github.com/softloft08-ship-it/box-maker123/blob/main/box.py"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Box Maker v{self.VERSION}")
        self.resize(1500, 950)
        self.setStyleSheet("QMainWindow { background: #000; } QLabel { color: #ccc; } QPushButton { background: #222; color: #fff; padding: 10px; border: 1px solid #444; }")
        
        central = QWidget(); self.setCentralWidget(central); main_layout = QHBoxLayout(central)
        self.renderer = BoxRenderer(); main_layout.addWidget(self.renderer, 4)
        panel_area = QScrollArea(); panel_area.setFixedWidth(350); panel_area.setWidgetResizable(True)
        panel = QWidget(); panel_layout = QVBoxLayout(panel); panel_area.setWidget(panel); main_layout.addWidget(panel_area, 1)

        self.drag_toggle = QCheckBox("DRAG MODE (LOCK CAMERA)"); self.drag_toggle.setStyleSheet("color: #0f0; font-weight: bold;")
        self.drag_toggle.stateChanged.connect(self.toggle_drag); panel_layout.addWidget(self.drag_toggle)

        panel_layout.addWidget(QLabel("<b>TEXT LAYERS</b>"))
        self.layer_list = QListWidget(); self.layer_list.currentRowChanged.connect(self.select_l); panel_layout.addWidget(self.layer_list)
        self.text_input = QLineEdit(); self.text_input.textChanged.connect(self.upd_text); panel_layout.addWidget(self.text_input)
        self.size_spin = QSpinBox(); self.size_spin.setRange(10, 500); self.size_spin.valueChanged.connect(self.upd_style); panel_layout.addWidget(self.size_spin)
        self.font_combo = QComboBox(); self.font_combo.addItems(["arial.ttf", "impact.ttf", "verdana.ttf", "times.ttf", "comic.ttf"]); self.font_combo.currentTextChanged.connect(self.upd_font); panel_layout.addWidget(self.font_combo)
        btn_col = QPushButton("Text Color"); btn_col.clicked.connect(self.set_t_col); panel_layout.addWidget(btn_col)
        btn_add = QPushButton("+ Add Text"); btn_add.clicked.connect(self.add_t); panel_layout.addWidget(btn_add)
        btn_rem = QPushButton("🗑 Remove Text"); btn_rem.clicked.connect(self.rem_t); panel_layout.addWidget(btn_rem)

        panel_layout.addWidget(QLabel("<b>ASSETS</b>"))
        btn_w = QPushButton("Box Wrap"); btn_w.clicked.connect(self.set_w); panel_layout.addWidget(btn_w)
        btn_bg = QPushButton("Background"); btn_bg.clicked.connect(self.set_bg); panel_layout.addWidget(btn_bg)
        btn_i = QPushButton("Add Icon"); btn_i.clicked.connect(self.add_i); panel_layout.addWidget(btn_i)
        
        self.timer = QTimer(); self.timer.timeout.connect(self.renderer.update); self.timer.start(16)
        
        # Start update check after window loads
        QTimer.singleShot(2000, self.check_for_updates)

    def check_for_updates(self):
        try:
            r = requests.get(self.VERSION_URL, timeout=5)
            if r.status_code == 200 and r.text.strip() != self.VERSION:
                ret = QMessageBox.question(self, "Update Available", 
                                         f"New version {r.text.strip()} found. Update now?", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ret == QMessageBox.StandardButton.Yes:
                    self.perform_update()
        except Exception as e:
            print(f"Check failed: {e}")

    def perform_update(self):
        try:
            new_code = requests.get(self.UPDATE_URL).text
            # Overwrite THIS very file with the new code
            with open(__file__, "w", encoding="utf-8") as f:
                f.write(new_code)
            QMessageBox.information(self, "Updated!", "Update installed. Please restart the app to see changes.")
            sys.exit()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Update failed: {e}")

    # (Previous helper methods for text/icons remain the same)
    def toggle_drag(self, state): 
        self.renderer.drag_mode = (state == 2)
        if state == 2: self.renderer.x_rot, self.renderer.y_rot = 0, 0
    def select_l(self, i):
        if i >= 0:
            l = self.renderer.text_layers[i]; self.text_input.setText(l['text']); self.size_spin.setValue(l['size'])
    def upd_text(self):
        i = self.layer_list.currentRow()
        if i >= 0: self.renderer.text_layers[i]['text'] = self.text_input.text(); self.layer_list.item(i).setText(self.text_input.text()); self.renderer.needs_texture_update = True
    def upd_style(self):
        i = self.layer_list.currentRow()
        if i >= 0: self.renderer.text_layers[i]['size'] = self.size_spin.value(); self.renderer.needs_texture_update = True
    def upd_font(self, f):
        i = self.layer_list.currentRow()
        if i >= 0: self.renderer.text_layers[i]['font'] = f; self.renderer.needs_texture_update = True
    def set_t_col(self):
        i = self.layer_list.currentRow()
        if i >= 0:
            c = QColorDialog.getColor()
            if c.isValid(): self.renderer.text_layers[i]['color'] = (c.red(), c.green(), c.blue(), 255); self.renderer.needs_texture_update = True
    def add_t(self):
        self.renderer.text_layers.append({'text': "EDIT ME", 'x': 400, 'y': 400, 'size': 80, 'color': (255,255,255,255), 'font': "arial.ttf", 'rect': QRect()})
        self.layer_list.addItem("EDIT ME"); self.renderer.needs_texture_update = True
    def rem_t(self):
        i = self.layer_list.currentRow()
        if i >= 0: self.renderer.text_layers.pop(i); self.layer_list.takeItem(i); self.renderer.needs_texture_update = True
    def set_w(self):
        p, _ = QFileDialog.getOpenFileName(self, "Wrap")
        if p: self.renderer.img_path = p; self.renderer.needs_texture_update = True
    def set_bg(self):
        p, _ = QFileDialog.getOpenFileName(self, "Background")
        if p:
            img = Image.open(p).convert("RGBA")
            self.renderer.makeCurrent()
            self.renderer.bg_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.renderer.bg_texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.size[0], img.size[1], 0, GL_RGBA, GL_UNSIGNED_BYTE, img.tobytes())
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    def add_i(self):
        p, _ = QFileDialog.getOpenFileName(self, "Icon")
        if p: self.renderer.icons.append({'path': p, 'x': 300, 'y': 300, 'w': 150, 'h': 150, 'rect': QRect()}); self.renderer.needs_texture_update = True

if __name__ == "__main__":

    app = QApplication(sys.argv); w = MainWindow(); w.show(); sys.exit(app.exec())

