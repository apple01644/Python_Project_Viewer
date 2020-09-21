import colorsys
import datetime
import math
import random
import statistics
from math import sin, cos
import sys

import numpy.matlib
import pygame.locals


def matrix_scale(x=1, y=1, z=1, w=1):
    return numpy.array([
        [x, 0, 0, 0],
        [0, y, 0, 0],
        [0, 0, z, 0],
        [0, 0, 0, w],
    ])


def matrix_rotate_xyz(x=0, y=0):
    return numpy.dot(numpy.array([
        [1, 0, 0, 0],
        [0, +cos(x), -sin(x), 0],
        [0, +sin(x), +cos(x), 0],
        [0, 0, 0, 1],
    ]), numpy.array([
        [+cos(y), 0, +sin(y), 0],
        [0, 1, 0, 0],
        [-sin(y), 0, +cos(y), 0],
        [0, 0, 0, 1],
    ]))


def matrix_rotate_with_vector(vec3: list, rad):
    ux = vec3[0]
    uy = vec3[1]
    uz = vec3[2]
    return numpy.array([
        [numpy.cos(rad) + (ux ** 2) * (1 - numpy.cos(rad)), ux * uy * (1 - numpy.cos(rad)) - uz * numpy.sin(rad),
         ux * uz * (1 - numpy.cos(rad)) + uy * numpy.sin(rad), 0],
        [uy * ux * (1 - numpy.cos(rad)) + uz * numpy.sin(rad), numpy.cos(rad) + (uy ** 2) * (1 - numpy.cos(rad)),
         uy * uz * (1 - numpy.cos(rad)) - ux * numpy.sin(rad), 0],
        [uz * ux * (1 - numpy.cos(rad)) - uy * numpy.sin(rad), uz * uy * (1 - numpy.cos(rad)) + ux * numpy.sin(rad),
         numpy.cos(rad) + (uz ** 2) * (1 - numpy.cos(rad)), 0],
        [0, 0, 0, 1],
    ])


def matrix_translate(x=0, y=0, z=0):
    return numpy.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1],
    ])


def points_distance(vector_a, vector_b):
    return ((vector_a[0] - vector_b[0]) ** 2 + (vector_a[1] - vector_b[1]) ** 2 + (
            vector_a[2] - vector_b[2]) ** 2) ** 0.5


def homogeneous_coordinates_matrix():
    return numpy.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
    ])


class Vertex:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

        self.color_h = math.atan2(self.y, self.x) / (numpy.pi * 2) + 0.5
        self.color_s = 0.8
        self.color_v = 1
        self.color_fix_v = False

        self.vx = 0
        self.vy = 0
        self.vz = 0
        self.size = 7

    def get_pos(self):
        return [self.x, self.y, self.z]

    def add_force(self, v):
        self.vx += v[0]
        self.vy += v[1]
        self.vz += v[2]

    def set_pos(self, v):
        self.x = v[0]
        self.y = v[1]
        self.z = v[2]


class RelationInfo:
    def __init__(self, model, A, B):
        self.vertex_a = model.vertexes[A]
        self.vertex_b = model.vertexes[B]
        self.detail_a = model.relation_data[A]
        self.detail_b = model.relation_data[B]
        self.vector_a_to_b = [self.vertex_b.get_pos()[k] - self.vertex_a.get_pos()[k] for k in range(3)]
        self.vector_a_to_b_length = points_distance(self.vertex_a.get_pos(), self.vertex_b.get_pos())
        self.equal_top_dir = self.detail_a['top_dir'] == self.detail_b['top_dir']
        self.is_a_external = self.detail_a['top_dir'] == '__external__'
        self.is_b_external = self.detail_b['top_dir'] == '__external__'
        self.a_import_b = (B in self.detail_a['imports'])
        self.b_import_a = (A in self.detail_b['imports'])


def get_fit_size_of_singleline_for_circle(drawing_plain_fonts, line, radius):
    last_size = None
    for size in range(len(drawing_plain_fonts)):
        text = drawing_plain_fonts[size].render(line, True, (0, 0, 0))
        if text.get_width() <= radius * 2 or (last_size is None):
            last_size = size
        else:
            break
    return last_size


def get_fit_size_of_mutipleline_text_for_circle(drawing_plain_fonts, lines, radius):
    last_size = None
    line_height = None
    for size in range(len(drawing_plain_fonts)):
        text = drawing_plain_fonts[size].render('examine text', True, (0, 0, 0))
        if text.get_height() * len(lines) <= radius * 2 or (last_size is None):
            if last_size is None:
                last_size = size
                line_height = text.get_height()
            else:
                is_fit = True
                for line in lines:
                    line_text = drawing_plain_fonts[size].render(line, True, (0, 0, 0))
                    if not (line_text.get_width() <= radius * 2):
                        is_fit = False
                        break
                if is_fit:
                    last_size = size
                    line_height = text.get_height()
        else:
            break

    return last_size, line_height


class PyUIWidget:
    def __init__(self, tag, **kwargs):
        self.tag = tag
        self.attribute = {}
        self.rect = [0, 0, 0, 0]

        if self.tag == 'checkbox':
            self.attribute['is_checked'] = False
        elif self.tag == 'scrollbar':
            self.attribute['scroll_value'] = 33
        elif self.tag == 'text':
            self.attribute['text'] = ''

        for key in kwargs:
            self.attribute[key] = kwargs[key]

    @staticmethod
    def draw_label(window_surf, work_on_rect, drawing_plain_font, widget, x=0, new_line=True):
        text_solid = drawing_plain_font.render(widget.attribute['label'], True, (0, 0, 0))
        window_surf.blit(text_solid,
                         (work_on_rect[0] + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2))
        if widget.tag == 'title':
            window_surf.blit(text_solid,
                             (work_on_rect[0] + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2 + 1))
        widget.rect = [work_on_rect[0] + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2, text_solid.get_width(), text_solid.get_height()]
        if new_line:
            work_on_rect[1] += 30
            work_on_rect[3] -= 30

    @staticmethod
    def draw_text(window_surf, work_on_rect, drawing_plain_font, widget, x=0, new_line=True):
        width = 0
        height = 0
        for line in widget.attribute['text'].split('\n'):
            text_solid = drawing_plain_font.render(line, True, (0, 0, 0))
            window_surf.blit(text_solid, (work_on_rect[0] + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2 + height))
            width = max(width, text_solid.get_width())
            height += 30
        widget.rect = [work_on_rect[0] + x, work_on_rect[1], width, height]
        if new_line:
            work_on_rect[1] += height
            work_on_rect[3] -= height

    @staticmethod
    def draw_label(window_surf, work_on_rect, drawing_plain_font, widget, x=0, new_line=True):
        text_solid = drawing_plain_font.render(widget.attribute['label'], True, (0, 0, 0))
        window_surf.blit(text_solid,
                         (work_on_rect[0] + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2))
        if widget.tag == 'title':
            window_surf.blit(text_solid,
                             (work_on_rect[0] + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2 + 1))
        widget.rect = [work_on_rect[0] + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2, text_solid.get_width(), text_solid.get_height()]
        if new_line:
            work_on_rect[1] += 30
            work_on_rect[3] -= 30

    @staticmethod
    def draw_checkbox(window_surf, work_on_rect, drawing_plain_font, widget, x=0, new_line=True):
        pygame.draw.rect(window_surf, [0, 0, 0], (work_on_rect[0] + x, work_on_rect[1], 22, 22))
        pygame.draw.rect(window_surf, [255, 255, 255],
                         (work_on_rect[0] + x + 1, work_on_rect[1] + 1, 20, 20))

        if widget.attribute['is_checked']:
            pygame.draw.polygon(window_surf, [0, 0, 0], [
                (work_on_rect[0] + x + 3, work_on_rect[1] + 13),
                (work_on_rect[0] + x + 9, work_on_rect[1] + 18),
                (work_on_rect[0] + x + 18, work_on_rect[1] + 3),
                (work_on_rect[0] + x + 8, work_on_rect[1] + 15),
            ])

        text_solid = drawing_plain_font.render(widget.attribute['label'], True, (0, 0, 0))
        window_surf.blit(text_solid,
                         (work_on_rect[0] + 26 + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2))
        widget.rect = [work_on_rect[0] + x, work_on_rect[1], 22, 22]
        if new_line:
            work_on_rect[1] += 30
            work_on_rect[3] -= 30

    @staticmethod
    def draw_scroll_bar(window_surf, work_on_rect, drawing_plain_font, widget, x=0, new_line=True):
        text_solid = drawing_plain_font.render(widget.attribute['label'], True, (0, 0, 0))
        window_surf.blit(text_solid,
                         (work_on_rect[0] + 2 + x, work_on_rect[1] + (22 - text_solid.get_height()) // 2))
        pygame.draw.rect(window_surf, [120, 120, 120], (work_on_rect[0] + x, work_on_rect[1] + 32, 260, 2))
        pygame.draw.rect(window_surf, [177, 195, 217], (
            work_on_rect[0] + x + int(widget.attribute['scroll_value'] * 260 / 100) - 2, work_on_rect[1] + 22, 4, 22))
        widget.rect = [work_on_rect[0] + x, work_on_rect[1] + 22, 260, 22]
        if new_line:
            work_on_rect[1] += 60
            work_on_rect[3] -= 60


class ModelVisualizer:

    def __init__(self):
        self.widget_title = PyUIWidget(tag='title', label='')
        self.widget_description = PyUIWidget(tag='text', label='')
        self.widget_enable_strict_select_mode = PyUIWidget(tag='checkbox', label='Enable Narrowed Select')
        self.widget_enable_drawing_relation = PyUIWidget(tag='checkbox', label='Enable Drawing All Relations')
        self.widget_enable_drawing_vertex_names = PyUIWidget(tag='checkbox', label='Enable Drawing Vertex names')
        self.widget_enable_drawing_group_names = PyUIWidget(tag='checkbox', label='Enable Drawing Group names')
        self.widget_width_relations = PyUIWidget(tag='scrollbar', label='Witdh Relations')
        self.widget_scale_vertex_name = PyUIWidget(tag='scrollbar', label='Scale of Vertex\'s Name')
        self.widget_scale_vertex = PyUIWidget(tag='scrollbar', label='Scale of Vertexes')

        self.window_w = 1024
        self.menu_panel_width = 300
        self.window_h = 768
        self.window_surf = None

        self.stop_loop = False

        self.vertexes = {}
        self.top_dirs = {}
        self.relation_data = {}

        self.t = 0.0
        self.dt = 0.0

        self.selected_uuid = None

        self.relation_view = numpy.matlib.identity(4)

        self.max_physics_time = 40

        self.widgets = []

        self.initialize_user_interface()

    def initialize_user_interface(self):
        self.widget_enable_drawing_vertex_names.attribute['is_checked'] = True
        self.widget_enable_drawing_group_names.attribute['is_checked'] = True
        self.widget_enable_drawing_relation.attribute['is_checked'] = True

        self.widgets.append(self.widget_scale_vertex)
        self.widgets.append(self.widget_scale_vertex_name)
        self.widgets.append(self.widget_width_relations)
        self.widgets.append(self.widget_enable_drawing_vertex_names)
        self.widgets.append(self.widget_enable_drawing_group_names)
        self.widgets.append(self.widget_enable_drawing_relation)
        self.widgets.append(self.widget_enable_strict_select_mode)
        self.widgets.append(self.widget_title)
        self.widgets.append(self.widget_description)

    def analyze_model(self, file_name):
        with open(file_name, 'r') as file:
            self.relation_data = eval(file.read())
            for module_id in self.relation_data:
                relation = self.relation_data[module_id]
                self.vertexes[module_id] = Vertex(random.uniform(-1, +1), random.uniform(-1, +1),
                                                  random.uniform(-1, +1))
                self.vertexes[module_id].size += len(relation['imports']) * 2

                if relation['top_dir'] != '__external__':
                    if not (relation['top_dir'] in self.top_dirs):
                        self.top_dirs[relation['top_dir']] = {}
                    relation['mod_name'] = relation['abs_path'] \
                        .replace(f'/{relation["top_dir"]}/', '') \
                        .replace('.py', '') \
                        .replace('/', '.')
                else:
                    relation['mod_name'] = relation['abs_path'][len('external://'):]

            k = 0
            for top_dir in self.top_dirs:
                if top_dir != '__external__':
                    self.top_dirs[top_dir]['color'] = k / (len(self.top_dirs))
                    self.top_dirs[top_dir]['pos'] = [random.uniform(-1, +1), random.uniform(-1, +1),
                                                     random.uniform(-1, +1)]
                    k += 1

            for module_id in self.vertexes:
                vertex = self.vertexes[module_id]
                relation = self.relation_data[module_id]
                for other_module_id in relation['imports']:
                    self.vertexes[other_module_id].size += 2

                if relation['top_dir'] != '__external__':
                    top_dir = self.top_dirs[relation['top_dir']]
                    vertex.color_h = top_dir['color']
                    vertex.set_pos([k + random.uniform(-1e-2, +1e-2) for k in top_dir['pos']])
                else:
                    vertex.color_h = 0
                    vertex.color_s = 0
                    vertex.color_fix_v = True
                    vertex.color_v = 0.75

    def get_selected_imports_list(self, drawing_title_font):
        relation = self.relation_data[self.selected_uuid]
        text = f'this is import ({len(relation["imports"])}) modules\n'

        for item in self.relation_data[self.selected_uuid]['imports']:
            text += self.relation_data[item]['abs_path'].replace('external://', 'ext://') + '\n'

        return text

    def draw_groups(self, drawing_groups, drawing_title_font):
        for group_name in drawing_groups:
            group = drawing_groups[group_name]
            if len(group['members']) > 1:
                group_x = statistics.median(group['pos'][0])
                group_y = statistics.median(group['pos'][1])
                rgb_color = [int(k * 255) for k in colorsys.hsv_to_rgb(group['color_h'], 0.15, 1)]
                if 0 < group_x < (self.window_w - self.menu_panel_width) and 0 < group_y < self.window_h:
                    self.draw_string_and_its_outline(drawing_title_font, group_name.upper(), group_x, group_y,
                                                     color=rgb_color)

    def list_drawing_circles(self, drawing_scale):
        drawing_circles = []
        sum_of_depth = 0
        circle_scale = (self.widget_scale_vertex.attribute['scroll_value'] / 33) ** 2

        for module_id in self.vertexes:
            vertex = self.vertexes[module_id]
            pos_on_screen = self.vertex_position_on_screen(vertex)
            if pos_on_screen[2] >= 1:
                radius = int(numpy.ceil(vertex.size * drawing_scale / pos_on_screen[3] * circle_scale))
                if radius > 2:
                    color_v = (0.75 + 0.25 / pos_on_screen[3]) if not vertex.color_fix_v else vertex.color_v
                    color_rgb = [int(value * 255)
                                 for value in colorsys.hsv_to_rgb(vertex.color_h, vertex.color_s, color_v)]

                    drawing_circles.append({
                        'uuid': module_id,
                        'color': color_rgb,
                        'pos': (int(pos_on_screen[0]), int(pos_on_screen[1])),
                        'radius': radius,
                        'depth': pos_on_screen[3]
                    })
                sum_of_depth += pos_on_screen[3]
        return drawing_circles, sum_of_depth

    def draw_circles_and_get_circle_groups(self, drawing_circles, average_of_depth, drawing_plain_fonts):
        drawing_groups = {}
        circle_scale = (self.widget_scale_vertex.attribute['scroll_value'] / 33) ** 2
        name_scale = (self.widget_scale_vertex_name.attribute['scroll_value'] / 33) ** 2

        for circle in drawing_circles:
            if circle['uuid'] == self.selected_uuid:
                pygame.draw.circle(self.window_surf, [0, 0, 0], circle['pos'], circle['radius'] + 3)
            else:
                pygame.draw.circle(self.window_surf, [0, 0, 0], circle['pos'], circle['radius'] + 1)
            pygame.draw.circle(self.window_surf, circle['color'], circle['pos'], circle['radius'])

            if circle['depth'] < average_of_depth:
                if self.widget_enable_drawing_vertex_names.attribute['is_checked']:
                    lines = [line.strip() for line in self.relation_data[circle['uuid']]['mod_name'].split('.') if len(line.strip()) > 0]
                    is_multilines = len(lines) > 1
                    if is_multilines:
                        fit_size, line_height = get_fit_size_of_mutipleline_text_for_circle(drawing_plain_fonts, lines,
                                                                                            circle[
                                                                                                'radius'] * name_scale * circle_scale)
                        for y_index, line in enumerate(lines):
                            y_proportion = (y_index / (len(lines) - 1) - 0.5) * 2
                            self.draw_string_and_its_outline(drawing_plain_fonts[fit_size], line, circle['pos'][0],
                                                             circle['pos'][1] + line_height * y_proportion)
                    else:
                        line = lines[0]
                        fit_size = get_fit_size_of_singleline_for_circle(drawing_plain_fonts, line,
                                                                         circle['radius'] * name_scale * circle_scale)
                        self.draw_string_and_its_outline(drawing_plain_fonts[fit_size], line, circle['pos'][0],
                                                         circle['pos'][1])
                self.insert_vertex_to_groups(circle, drawing_groups)
        return drawing_groups

    def draw_string_and_its_shadow(self, drawing_font, text, x, y):
        text_shadow = drawing_font.render(text, True, (0, 0, 0))
        text_solid = drawing_font.render(text, True, (255, 255, 255))
        self.window_surf.blit(text_shadow,
                              (x + 2 - text_shadow.get_width() // 2, y + 2 - text_shadow.get_height() // 2))
        self.window_surf.blit(text_solid, (x - text_solid.get_width() // 2, y - text_solid.get_height() // 2))

    def draw_string_and_its_outline(self, drawing_font, text, x, y, color=[255, 255, 255]):
        text_shadow = drawing_font.render(text, True, (0, 0, 0))
        text_solid = drawing_font.render(text, True, color)
        self.window_surf.blit(text_shadow,
                              (x + 1 - text_shadow.get_width() // 2, y + 1 - text_shadow.get_height() // 2))
        self.window_surf.blit(text_shadow,
                              (x + 1 - text_shadow.get_width() // 2, y - 1 - text_shadow.get_height() // 2))
        self.window_surf.blit(text_shadow,
                              (x - 1 - text_shadow.get_width() // 2, y + 1 - text_shadow.get_height() // 2))
        self.window_surf.blit(text_shadow,
                              (x - 1 - text_shadow.get_width() // 2, y - 1 - text_shadow.get_height() // 2))
        self.window_surf.blit(text_solid, (x - text_solid.get_width() // 2, y - text_solid.get_height() // 2))

    def insert_vertex_to_groups(self, circle, drawing_groups):
        info = self.relation_data[circle['uuid']]
        if info['top_dir'] != '__external__':
            if not (info['top_dir'] in drawing_groups):
                group = {}
                group['members'] = []
                group['pos'] = [[], []]
                group['color_h'] = self.top_dirs[info['top_dir']]['color']
                drawing_groups[info['top_dir']] = group

            drawing_groups[info['top_dir']]['members'].append(circle['uuid'])
            for k in range(2):
                drawing_groups[info['top_dir']]['pos'][k].append(circle['pos'][k])

    def vertex_position_on_screen(self, vertex):
        tpos = self.relation_view.dot([vertex.x, vertex.y, vertex.z, 1]).tolist()[0]
        if tpos[2] >= 1:
            tpos[0] /= tpos[2]
            tpos[1] /= tpos[2]
        else:
            tpos[0] = math.nan
            tpos[1] = math.nan
        return tpos

    def each_relation(self, callback):
        for A in self.vertexes:
            for B in self.vertexes:
                if A != B:
                    callback(A, B, RelationInfo(self, A, B))

    def draw_relations(self, drawing_circles):
        lines = []
        for A in drawing_circles:
            for B in drawing_circles:
                if A['uuid'] != B['uuid']:
                    info = RelationInfo(self, A['uuid'], B['uuid'])
                    if self.widget_enable_strict_select_mode.attribute['is_checked']:
                        suppose_to_draw_relation = (A['uuid'] == self.selected_uuid or B['uuid'] == self.selected_uuid)
                    else:
                        if self.selected_uuid:
                            suppose_to_draw_relation = \
                                info.detail_a['top_dir'] == self.relation_data[self.selected_uuid]['top_dir'] \
                                or info.detail_b['top_dir'] == self.relation_data[self.selected_uuid]['top_dir']
                        else:
                            suppose_to_draw_relation = self.widget_enable_drawing_relation.attribute['is_checked']
                    if info.a_import_b and (not info.is_a_external) and suppose_to_draw_relation:
                        a_2d_pos = self.vertex_position_on_screen(info.vertex_a)
                        b_2d_pos = self.vertex_position_on_screen(info.vertex_b)
                        if a_2d_pos[2] >= 1 and b_2d_pos[2] >= 1:
                            lines.append({
                                'color': [255 * k for k in
                                              colorsys.hsv_to_rgb(info.vertex_a.color_h, info.vertex_a.color_s, 1)],
                                'start_pos':(int(a_2d_pos[0]), int(a_2d_pos[1])),
                                'end_pos':(int(b_2d_pos[0]), int(b_2d_pos[1])),
                            })

        width = int(self.widget_width_relations.attribute['scroll_value'] ** 2 / 33 / 33)
        for line in lines:
            pygame.draw.line(self.window_surf, line['color'], line['start_pos'], line['end_pos'], width)

    def listen_event_user_interface(self, event):
        if event.type == pygame.locals.MOUSEBUTTONDOWN or event.type == pygame.locals.MOUSEBUTTONUP or event.type == pygame.locals.MOUSEMOTION:
            pos = event.pos
            if self.window_w - self.menu_panel_width <= pos[0] <= self.window_w:
                for widget in reversed(self.widgets):
                    if widget.rect[0] <= pos[0] <= widget.rect[0] + widget.rect[2] and \
                            widget.rect[1] <= pos[1] <= widget.rect[1] + widget.rect[3]:
                        if widget.tag == 'checkbox':
                            if event.type == pygame.locals.MOUSEBUTTONUP:
                                widget.attribute['is_checked'] = not widget.attribute['is_checked']
                        elif widget.tag == 'scrollbar':
                            if event.type == pygame.locals.MOUSEMOTION:
                                if pygame.mouse.get_pressed()[0]:
                                    widget.attribute['scroll_value'] = int(
                                        (pos[0] - widget.rect[0]) / widget.rect[2] * 100)
                return True
        return False

    def draw_user_interfaces(self, drawing_plain_font, drawing_title_font):
        # Preset
        pygame.draw.rect(self.window_surf, [153, 180, 209],
                         (self.window_w - self.menu_panel_width, 0, self.menu_panel_width, self.window_h))
        pygame.draw.rect(self.window_surf, [240, 240, 240], (
            self.window_w - self.menu_panel_width + 2, 19, self.menu_panel_width - 2 - 24, self.window_h - 19 - 2))
        pygame.draw.rect(self.window_surf, [177, 195, 217],
                         (self.window_w - self.menu_panel_width, 0, self.menu_panel_width - 24, 19))

        work_on_rect = [self.window_w - self.menu_panel_width + 12, 29, self.menu_panel_width - 2 - 24 - 10 * 2,
                        self.window_h - 19 - 2 - 10 * 2]

        for widget in self.widgets:
            if widget.tag == 'checkbox':
                PyUIWidget.draw_checkbox(self.window_surf, work_on_rect, drawing_plain_font, widget)
            elif widget.tag == 'scrollbar':
                PyUIWidget.draw_scroll_bar(self.window_surf, work_on_rect, drawing_plain_font, widget)
            elif widget.tag == 'label':
                PyUIWidget.draw_label(self.window_surf, work_on_rect, drawing_plain_font, widget)
            elif widget.tag == 'title':
                PyUIWidget.draw_label(self.window_surf, work_on_rect, drawing_plain_font, widget)
            elif widget.tag == 'text':
                PyUIWidget.draw_text(self.window_surf, work_on_rect, drawing_plain_font, widget)

        if self.selected_uuid:
            self.widget_description.attribute['text'] = self.get_selected_imports_list(drawing_title_font)
        else:
            self.widget_description.attribute['text'] = ''

    def working_between_relations(self, A, B, info: RelationInfo):
        if info.equal_top_dir:
            if not (info.is_a_external or info.is_b_external):
                if info.vector_a_to_b_length > 0.6:
                    factor = 0.0 * (info.vector_a_to_b_length - 0.6)
                    info.vertex_a.add_force([+k * self.dt * factor for k in info.vector_a_to_b])
                    info.vertex_b.add_force([-k * self.dt * factor for k in info.vector_a_to_b])
                elif info.vector_a_to_b_length < 0.2:
                    factor = -1.9 * (0.2 - info.vector_a_to_b_length)
                    info.vertex_a.add_force([+k * self.dt * factor for k in info.vector_a_to_b])
                    info.vertex_b.add_force([-k * self.dt * factor for k in info.vector_a_to_b])
        else:
            factor = -0.1
            if info.is_a_external or info.is_b_external:
                factor = -0.3
            if info.vector_a_to_b_length < 0.4:
                info.vertex_a.add_force([+k * self.dt * factor for k in info.vector_a_to_b])
                info.vertex_b.add_force([-k * self.dt * factor for k in info.vector_a_to_b])

    def module_physic(self, physics_speed):
        self.each_relation(self.working_between_relations)

        for vertex in self.vertexes.values():
            vertex.x += vertex.vx * self.dt * physics_speed
            vertex.y += vertex.vy * self.dt * physics_speed
            vertex.z += vertex.vz * self.dt * physics_speed

            length = points_distance(vertex.get_pos(), [0, 0, 0])
            if length != 1:
                vertex.set_pos([vertex.get_pos()[k] / length for k in range(3)])

    def prepare_vertex_position(self):
        for tick in range(self.max_physics_time):
            self.dt = 0.25
            self.module_physic(1 / (1 + tick / 4))

    def caculate_drawing_view(self, rotation_view, drawing_scale):
        self.relation_view = numpy.matlib.identity(4)
        self.relation_view *= matrix_translate((self.window_w - self.menu_panel_width) // 2, self.window_h // 2)
        self.relation_view *= homogeneous_coordinates_matrix()
        self.relation_view *= matrix_scale(
            min(self.window_w - self.menu_panel_width, self.window_h) * 0.45 * drawing_scale,
            min(self.window_w - self.menu_panel_width, self.window_h) * 0.45 * drawing_scale)
        self.relation_view *= matrix_translate(0, 0, 2)
        self.relation_view *= rotation_view

    def main_loop(self):
        pygame.init()
        pygame.display.set_caption('Model Visualizer')

        self.window_surf = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

        drawing_plain_fonts = []
        drawing_title_font = pygame.font.SysFont("Seogu UI", 32)
        for _ in range(48):
            drawing_plain_fonts.append(pygame.font.SysFont("Consolas", 10 + _))

        rotation_view = numpy.matlib.identity(4)

        drawing_scale = 1
        drawing_circles = []

        self.caculate_drawing_view(rotation_view, drawing_scale)

        timer_start = datetime.datetime.now()
        while not self.stop_loop:
            timer_end = datetime.datetime.now()
            timer_duration = timer_end - timer_start
            self.dt = timer_duration.microseconds / 1000000
            self.t += self.dt
            timer_start = datetime.datetime.now()

            for event in pygame.event.get():
                if event.type == pygame.locals.QUIT:
                    self.stop_loop = True
                elif event.type == pygame.VIDEORESIZE:
                    if event.w != self.window_w or event.h != self.window_h:
                        self.window_w = event.w
                        self.window_h = event.h
                        self.window_surf = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
                        self.caculate_drawing_view(rotation_view, drawing_scale)
                elif event.type == pygame.locals.KEYDOWN:
                    pass
                elif self.listen_event_user_interface(event):
                    pass
                elif event.type == pygame.locals.MOUSEMOTION:
                    if pygame.mouse.get_pressed()[0]:
                        rel = event.rel
                        rotation_axis_dx = +rel[1] / self.window_h * (2 * numpy.pi)
                        rotation_axis_dy = -rel[0] / (self.window_w - self.menu_panel_width) * (2 * numpy.pi)
                        rotation_view = numpy.dot(matrix_rotate_xyz(rotation_axis_dx, rotation_axis_dy), rotation_view)
                        self.caculate_drawing_view(rotation_view, drawing_scale)
                elif event.type == pygame.locals.MOUSEBUTTONDOWN:
                    if event.button == 3:
                        self.selected_uuid = None
                        self.widget_title.attribute['label'] = ''
                        for circle in reversed(drawing_circles):
                            if points_distance([circle['pos'][0], circle['pos'][1], 0], [event.pos[0], event.pos[1], 0]) \
                                    <= circle['radius']:
                                self.selected_uuid = circle['uuid']
                                self.widget_title.attribute['label'] = self.relation_data[circle['uuid']]['mod_path'].replace('external://', '')
                                break
                    elif event.button == 4:
                        drawing_scale *= 1.1
                        if drawing_scale > 5:
                            drawing_scale = 5
                        self.caculate_drawing_view(rotation_view, drawing_scale)
                    elif event.button == 5:
                        drawing_scale /= 1.1
                        if drawing_scale < 0.5:
                            drawing_scale = 0.5
                        self.caculate_drawing_view(rotation_view, drawing_scale)

            self.window_surf.fill((224, 235, 246))

            drawing_circles, sum_of_depth = self.list_drawing_circles(drawing_scale)

            if self.widget_width_relations.attribute['scroll_value'] >= 33:
                self.draw_relations(drawing_circles)

    
            drawing_circles.sort(key=lambda x: x['depth'], reverse=True)
            average_circle_depth = sum_of_depth / len(drawing_circles)
            drawing_groups = self.draw_circles_and_get_circle_groups(drawing_circles, average_circle_depth,
                                                                     drawing_plain_fonts)

            if self.widget_enable_drawing_group_names.attribute['is_checked']:
                self.draw_groups(drawing_groups, drawing_title_font)

            self.draw_user_interfaces(drawing_plain_fonts[4], drawing_title_font)
            pygame.display.flip()
        pygame.quit()


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print('Number of arguments is wrong.')
        print(f'python {sys.argv[0]} [INPUT_FILE_NAME]')
    else:
        print('[Start]Createing_Visualizer')
        model_visualizer = ModelVisualizer()

        print('[Start]Analyze Model')
        model_visualizer.analyze_model(sys.argv[1])

        print('[Start]Prepare Model Visualizer')
        model_visualizer.prepare_vertex_position()

        print('[Start]Main Loop')
        model_visualizer.main_loop()
        print('[Finish]')
