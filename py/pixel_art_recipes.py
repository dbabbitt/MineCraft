
#!/usr/bin/env python
# Utility Functions to build MineCraft pixel art
# Dave Babbitt <dave.babbitt@gmail.com>
# Author: Dave Babbitt, Data Scientist
# coding: utf-8
"""
PixelArtRecipies: A set of utility functions common to building MineCraft pixel art
"""
from IPython.display import HTML, display
from PIL import Image
from matplotlib.colors import to_hex
from pathlib import Path
import itertools
import math
import numpy as np
import operator
import os
import pandas as pd
import storage as s
import traceback
import webbrowser

import warnings
warnings.filterwarnings("ignore")

class PixelArtRecipies(object):
    """This class implements the core of the utility functions
    needed to play wordle.

    Examples
    --------

    >>> import sys
    >>> sys.path.insert(1, '../py')
    >>> import pixel_art_recipes
    >>> par = pixel_art_recipes.PixelArtRecipies()
    """

    def __init__(self):
        self.s = s.Storage()
        self.textures_dir = '../data/1.18.1_Default_Resource_Pack/assets/minecraft/textures/block'
        
        # Get RGB dictionaries
        if self.s.pickle_exists('AVERAGE_DICT') and self.s.pickle_exists('DOMINANT_DICT') and self.s.pickle_exists('WEIGHTED_AVERAGE_DICT'):
            self.average_dict = self.s.load_object('AVERAGE_DICT')
            self.dominant_dict = self.s.load_object('DOMINANT_DICT')
            self.weighted_average_dict = self.s.load_object('WEIGHTED_AVERAGE_DICT')
        else:
            def get_dictionaries(textures_dir, n_colors=5):
                average_dict = {}
                dominant_dict = {}
                weighted_dict = {}
                for file_name in os.listdir(textures_dir):
                    if file_name.endswith('.png'):
                        
                        # Read the image
                        file_path = os.path.join(textures_dir, file_name)
                        try:
                            img_array = io.imread(file_path)[:, :, :3]
                            if img_array.shape == (16, 16, 3):
                                
                                # Calculate the mean of each chromatic channel
                                average = img_array.mean(axis=0).mean(axis=0)
                                average_dict[file_name] = tuple(average)
                                
                                # Get the palette color which occurs most frequently
                                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
                                flags = cv2.KMEANS_RANDOM_CENTERS
                                pixels = np.float32(img_array.reshape(-1, 3))
                                _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags)
                                _, counts = np.unique(labels, return_counts=True)
                                dominant = palette[np.argmax(counts)]
                                dominant_dict[file_name] = tuple(dominant)
                                
                                # Calculate the mean of the palette patch
                                indices = np.argsort(counts)[::-1]   
                                freqs = np.cumsum(np.hstack([[0], counts[indices]/float(counts.sum())]))
                                rows = np.int_(img_array.shape[0]*freqs)
                                palette_patch = np.zeros(shape=img_array.shape, dtype=np.uint8)
                                for i in range(len(rows) - 1):
                                    palette_patch[rows[i]:rows[i + 1], :, :] += np.uint8(palette[indices[i]])
                                weighted_average = palette_patch.mean(axis=0).mean(axis=0)
                                weighted_dict[file_name] = tuple(weighted_average)
                        except IndexError as e:
                            print(f'{file_name}: {str(e).strip()}')
                
                return average_dict, dominant_dict, weighted_dict
            self.average_dict, self.dominant_dict, self.weighted_average_dict = get_dictionaries(self.textures_dir, n_colors=5)
            self.s.store_objects(AVERAGE_DICT=self.average_dict, DOMINANT_DICT=self.dominant_dict, WEIGHTED_AVERAGE_DICT=self.weighted_average_dict)
        
        # Get various block lists
        if self.s.pickle_exists('minecraft_glass_and_concrete_list') and self.s.pickle_exists('minecraft_concrete_list') and self.s.pickle_exists('minecraft_glass_list'):
            self.glass_and_concrete_list = self.s.load_object('minecraft_glass_and_concrete_list')
            self.concrete_list = self.s.load_object('minecraft_concrete_list')
            self.glass_list = self.s.load_object('minecraft_glass_list')
        else:
            self.glass_and_concrete_list = []
            self.concrete_list = []
            for file_name in self.average_dict.keys():
                if ('concrete' in file_name):
                    (img_array, avg_patch, dom_patch, palette_patch,
                     weighted_avg_patch) = get_patches(self.textures_dir, file_name, self.average_dict,
                                                       self.dominant_dict, self.weighted_average_dict)
                    show_images(file_name, img_array, avg_patch, dom_patch, palette_patch,
                                weighted_avg_patch)
                    self.glass_and_concrete_list.append(file_name)
                    self.concrete_list.append(file_name)
            self.glass_list = []
            for file_name in self.average_dict.keys():
                if ('glass' in file_name) and ('pane' not in file_name):
                    (img_array, avg_patch, dom_patch, palette_patch,
                     weighted_avg_patch) = get_patches(self.textures_dir, file_name, self.average_dict,
                                                       self.dominant_dict, self.weighted_average_dict)
                    show_images(file_name, img_array, avg_patch, dom_patch, palette_patch,
                                weighted_avg_patch)
                    self.glass_and_concrete_list.append(file_name)
                    self.glass_list.append(file_name)
            self.s.store_objects(minecraft_glass_and_concrete_list=self.glass_and_concrete_list, minecraft_concrete_list=self.concrete_list, minecraft_glass_list=self.glass_list)
        
        pickle_name = 'minecraft_glass_and_concrete_and_terracotta_list'
        if self.s.pickle_exists(pickle_name):
            self.glass_and_concrete_and_terracotta_list = self.s.load_object(pickle_name)
        else:
            self.glass_and_concrete_and_terracotta_list = self.glass_list + self.concrete_list
            self.glass_and_concrete_and_terracotta_list += [key for key in self.dominant_dict.keys() if 'terracotta' in key.lower()]
            self.s.store_objects(**{pickle_name: self.glass_and_concrete_and_terracotta_list})
        if self.s.pickle_exists('minecraft_glass_and_terracotta_list'):
            self.glass_and_terracotta_list = self.s.load_object('minecraft_glass_and_terracotta_list')
        else:
            self.glass_and_terracotta_list = self.glass_list + [key for key in self.dominant_dict.keys() if 'terracotta' in key.lower()]
            self.s.store_objects(minecraft_glass_and_terracotta_list=self.glass_and_terracotta_list)
        if self.s.pickle_exists('minecraft_terracotta_list'):
            terracotta_list = self.s.load_object('minecraft_terracotta_list')
        else:
            terracotta_list = [key for key in self.dominant_dict.keys() if 'terracotta' in key.lower()]
            self.s.store_objects(minecraft_terracotta_list=terracotta_list)
        
        pickle_name = 'minecraft_glass_and_concrete_and_unglazed_terracotta_list'
        if self.s.pickle_exists(pickle_name):
            self.glass_and_concrete_and_unglazed_terracotta_list = self.s.load_object(pickle_name)
        else:
            self.glass_and_concrete_and_unglazed_terracotta_list = []
            for fn in self.glass_and_concrete_and_terracotta_list:
                if 'glazed' not in fn:
                    self.glass_and_concrete_and_unglazed_terracotta_list.append(fn)
            self.s.store_objects(**{pickle_name: self.glass_and_concrete_and_unglazed_terracotta_list})
        
        pickle_name = 'minecraft_concrete_and_unglazed_terracotta_list'
        if self.s.pickle_exists(pickle_name):
            self.concrete_and_unglazed_terracotta_list = self.s.load_object(pickle_name)
        else:
            for fn in self.concrete_list + terracotta_list:
                if 'glazed' not in fn:
                    self.concrete_and_unglazed_terracotta_list.append(fn)
            self.s.store_objects(**{pickle_name: self.concrete_and_unglazed_terracotta_list})
        
        if self.s.pickle_exists('minecraft_blocks_list'):
            self.blocks_list = self.s.load_object('minecraft_blocks_list')
        else:
            self.blocks_list = ['acacia_log.png', 'acacia_log_top.png', 'acacia_planks.png',
                           'andesite.png', 'birch_log.png', 'birch_log_top.png',
                           'birch_planks.png', 'black_concrete.png', 'black_concrete_powder.png',
                           'black_glazed_terracotta.png', 'black_terracotta.png', 'black_wool.png',
                           'blue_concrete.png', 'blue_concrete_powder.png', 'blue_glazed_terracotta.png',
                           'blue_terracotta.png', 'blue_wool.png', 'bone_block_side.png',
                           'bone_block_top.png', 'bookshelf.png', 'bricks.png',
                           'brown_concrete.png', 'brown_concrete_powder.png', 'brown_glazed_terracotta.png',
                           'brown_terracotta.png', 'brown_wool.png', 'chiseled_nether_bricks.png',
                           'chiseled_quartz_block.png', 'chiseled_quartz_block_top.png',
                           'chiseled_red_sandstone.png',
                           'chiseled_sandstone.png', 'chiseled_stone_bricks.png', 'coal_block.png',
                           'coal_ore.png', 'cobblestone.png', 'cracked_nether_bricks.png',
                           'cracked_stone_bricks.png', 'cyan_concrete.png', 'cyan_concrete_powder.png',
                           'cyan_glazed_terracotta.png', 'cyan_terracotta.png', 'cyan_wool.png',
                           'dark_oak_log.png', 'dark_oak_log_top.png', 'dark_oak_planks.png',
                           'dark_prismarine.png', 'diamond_block.png', 'diorite.png',
                           'dirt.png', 'emerald_block.png', 'end_stone.png',
                           'end_stone_bricks.png', 'furnace_front.png', 'furnace_side.png',
                           'furnace_top.png', 'granite.png', 'grass_block_side.png',
                           'gravel.png', 'gray_concrete.png', 'gray_concrete_powder.png',
                           'gray_glazed_terracotta.png', 'gray_terracotta.png', 'gray_wool.png',
                           'green_concrete.png', 'green_concrete_powder.png',
                           'green_glazed_terracotta.png',
                           'green_terracotta.png', 'green_wool.png', 'hay_block_side.png',
                           'hay_block_top.png', 'iron_block.png', 'iron_ore.png',
                           'jack_o_lantern.png', 'jungle_log.png', 'jungle_log_top.png',
                           'jungle_planks.png', 'lapis_block.png', 'light_blue_concrete.png',
                           'light_blue_concrete_powder.png', 'light_blue_glazed_terracotta.png',
                           'light_blue_terracotta.png',
                           'light_blue_wool.png', 'light_gray_concrete.png',
                           'light_gray_concrete_powder.png',
                           'light_gray_glazed_terracotta.png', 'light_gray_terracotta.png',
                           'light_gray_wool.png',
                           'lime_concrete.png', 'lime_concrete_powder.png', 'lime_glazed_terracotta.png',
                           'lime_terracotta.png', 'lime_wool.png', 'magenta_concrete.png',
                           'magenta_concrete_powder.png', 'magenta_glazed_terracotta.png',
                           'magenta_terracotta.png',
                           'magenta_wool.png', 'melon_side.png', 'melon_top.png',
                           'mossy_cobblestone.png', 'mossy_stone_bricks.png', 'netherite_block.png',
                           'netherrack.png', 'nether_bricks.png', 'nether_quartz_ore.png',
                           'nether_wart_block.png', 'note_block.png', 'oak_log.png',
                           'oak_log_top.png', 'oak_planks.png', 'orange_concrete.png',
                           'orange_concrete_powder.png', 'orange_glazed_terracotta.png',
                           'orange_terracotta.png',
                           'orange_wool.png', 'packed_ice.png', 'pink_concrete.png',
                           'pink_concrete_powder.png', 'pink_glazed_terracotta.png', 'pink_terracotta.png',
                           'pink_wool.png', 'piston_side.png', 'piston_top.png',
                           'piston_top_sticky.png', 'podzol_side.png', 'polished_andesite.png',
                           'polished_diorite.png', 'polished_granite.png', 'prismarine_bricks.png',
                           'pumpkin_side.png', 'pumpkin_top.png', 'purple_concrete.png',
                           'purple_concrete_powder.png', 'purple_glazed_terracotta.png',
                           'purple_terracotta.png',
                           'purple_wool.png', 'purpur_block.png', 'purpur_pillar.png',
                           'purpur_pillar_top.png', 'quartz_block_side.png', 'quartz_block_top.png',
                           'quartz_bricks.png', 'quartz_pillar.png', 'quartz_pillar_top.png',
                           'redstone_block.png', 'redstone_lamp.png', 'redstone_ore.png',
                           'red_concrete.png', 'red_concrete_powder.png', 'red_glazed_terracotta.png',
                           'red_nether_bricks.png', 'red_sand.png', 'red_sandstone.png',
                           'red_sandstone_top.png', 'red_terracotta.png', 'red_wool.png',
                           'sand.png', 'sandstone.png', 'sandstone_top.png',
                           'slime_block.png', 'smooth_stone.png', 'smooth_stone_slab_side.png',
                           'soul_sand.png', 'sponge.png', 'spruce_log.png',
                           'spruce_log_top.png', 'spruce_planks.png', 'stone.png',
                           'stone_bricks.png', 'terracotta.png', 'wet_sponge.png',
                           'white_concrete.png', 'white_concrete_powder.png', 'white_glazed_terracotta.png',
                           'white_terracotta.png', 'white_wool.png', 'yellow_concrete.png',
                           'yellow_concrete_powder.png', 'yellow_glazed_terracotta.png',
                           'yellow_terracotta.png', 'yellow_wool.png']
            self.s.store_objects(minecraft_blocks_list=self.blocks_list)
        
        if self.s.pickle_exists('minecraft_wool_list'):
            self.wool_list = self.s.load_object('minecraft_wool_list')
        else:
            self.wool_list = [fn for fn in self.blocks_list if 'wool' in fn]
            self.s.store_objects(minecraft_wool_list=self.wool_list)
        self.unpowdered_and_unglazed_list = [fn for fn in self.concrete_and_unglazed_terracotta_list+self.wool_list if 'powder' not in fn.lower()]
        self.stained_glass_list = [key for key in self.weighted_average_dict.keys() if key.endswith('_stained_glass.png')]
    
    
    
    def conjunctify_nouns(self, noun_list):
        if len(noun_list) > 2:
            last_noun_str = noun_list[-1]
            but_last_nouns_str = ', '.join(noun_list[:-1])
            list_str = ', and '.join([but_last_nouns_str, last_noun_str])
        elif len(noun_list) == 2:
            list_str = ' and '.join(noun_list)
        elif len(noun_list) == 1:
            list_str = noun_list[0]
        else:
            list_str = ''
        
        return list_str
    
    
    
    def rgb_to_hex(self, rgb):
        
        return '%02x%02x%02x' % rgb
    
    
    
    def collate(self, blocks_list):
        it = itertools.groupby(blocks_list, operator.itemgetter(1))
        for key, subiter in it:
            
            yield key, list(item[0] for item in subiter)
    
    
    
    def pixel_to_filename(self, img_array, row, col, rgb_dict):
        f = lambda item: np.linalg.norm(np.array(item[1])-img_array[row][col])
        file_name = sorted(rgb_dict.items(), key=f)[0][0]
        
        return file_name
    
    
    
    def get_hex_str(self, rgb_dict, file_name):
        hex_str = to_hex(list(map(lambda x: x/255, rgb_dict[file_name])))
        
        return hex_str
    
    
    
    def get_block_name(self, file_name):
        block_name = file_name.split('.')[0].replace('_', ' ').title()
        
        return block_name
    
    
    
    def convert_rowcols_to_minecraft_coords(self, row, col):
        x = col - 495
        z = row + 207
        
        return x, z
    
    
    
    def get_column_markup(self, img_array, rgb_dict, td_style, img_style, row, col, text_html_str,
                          image_html_str, rows_list=[]):
        file_name = self.pixel_to_filename(img_array, row, col, rgb_dict)
        img_path = os.path.abspath(f'{self.textures_dir}/{file_name}')
        block_name = self.get_block_name(file_name)
        hex_str = self.get_hex_str(rgb_dict, file_name)
        x, z = self.convert_rowcols_to_minecraft_coords(row, col)
        text_html_str += f'<td title="X:{x} Z:{z}" style="background-color:{hex_str};text-align:center;">{block_name}</td>'
        image_html_str += f'<td title="X:{x} Z:{z} {block_name}" style="{td_style}">'
        image_html_str += f'<img src="file:///{img_path}" style="{img_style}" /></td>'
        row_dict = {}
        row_dict['row_number'] = row
        row_dict['column_number'] = col
        row_dict['block_name'] = block_name
        rows_list.append(row_dict)
        
        return rows_list, text_html_str, image_html_str
    
    
    
    def get_rowspan_markup(self, file_prefix, file_path, td_style, image_html_str, row_count, col_count):
        block_name = self.get_block_name(file_prefix)
        src_url = 'file:///' + os.path.abspath(file_path).replace(os.sep, '/')
        # image_str = f'<img src="{src_url}" style="display:block;" width="100%" height="100%" />'
        image_td_style = f"{td_style}background-image:url('{src_url}');background-size:cover;"
        image_td_style += 'background-position:center;'
        image_html_str += f'<td title="{block_name}" style="{image_td_style}" rowspan={row_count} '
        image_html_str += f'width="{col_count*16}px"></td>'
        
        return image_html_str
    
    
    
    def get_stack_summary(self, block_count, block_name, stacks_list):
        stack_count = (block_count // 64) + 1
        row_tuple = (block_name, stack_count)
        stacks_list.append(row_tuple)
        stack_str = 's' if stack_count > 1 else ''
        line_count = (block_count // (64*9)) + 1
        line_str = 's' if line_count > 1 else ''
        chest_count = (block_count // (64*9*3)) + 1
        chest_str = 's' if chest_count > 1 else ''
        it_str = 'them' if chest_count > 1 else 'it'
        summary_str = f'{block_name}: {block_count:,} '
        summary_str += f'({chest_count} chest{chest_str} with {line_count} line{line_str}/{stack_count} '
        summary_str += f'stack{stack_str} in {it_str}, total)'
        
        return stacks_list, summary_str
    
    
    
    def get_stack_collation(self, blocks_list, stack_count):
        if len(blocks_list) > 1:
            each_str = 'each '
        else:
            each_str = ''
        if stack_count > 1:
            s_str = 's'
        else:
            s_str = ''
        stack_collation = f'{stack_count} stack{s_str} {each_str}of {self.conjunctify_nouns(blocks_list)}.'
        
        return stack_collation
    
    
    
    def get_row_markup(self, text_html_str, image_html_str, rows_list, img_array, rgb_dict, td_style,
                       img_style, file_prefix, file_path,
                       col_start=0, col_count=10, row_start=0, row_count=10):
        text_html_str += '<tr>'
        image_html_str += '<tr>'
        for col in range(col_start, col_count):
            (rows_list, text_html_str,
             image_html_str) = self.get_column_markup(img_array, rgb_dict, td_style, img_style, row_start,
                                                 col, text_html_str, image_html_str, rows_list)
        text_html_str += '</tr>'
        if row_start==0:
            image_html_str = self.get_rowspan_markup(file_prefix, file_path, td_style, image_html_str,
                                                row_count, col_count)
        image_html_str += '</tr>'
        
        return text_html_str, image_html_str, rows_list
    
    
    
    def get_it_markup(self, file_path, rgb_dict, file_prefix, rows_list=[]):
        minecraft_pixel_art_img = Image.open(file_path)
        img_array = np.array(minecraft_pixel_art_img)
        row_count = img_array.shape[0]
        col_count = img_array.shape[1]
        td_style = 'padding:0;margin:0;'
        img_style = 'display:block;margin:0!important;padding:0!important;border:0!important;'
        text_html_str = image_html_str = '<table style="border-collapse:collapse;">'
        for row in range(row_count):
            (text_html_str, image_html_str,
             rows_list) = self.get_row_markup(text_html_str, image_html_str, rows_list, img_array, rgb_dict,
                                         td_style, img_style, file_prefix, file_path,
                                         col_start=0, col_count=col_count,
                                         row_start=row, row_count=row_count)
        text_html_str += '</table><hr />'
        image_html_str += '</table>'
        
        return text_html_str, image_html_str, rows_list
    
    
    
    def partition(self, lst, n):
        division = len(lst) / n
        
        return [lst[round(division * i):round(division * (i + 1))] for i in range(n)]
    
    
    
    def get_multiples(self, block_count, by_multiple=10):
        
        return [(r.start, r.stop) for r in self.partition(range(block_count), block_count // by_multiple)]
    
    
    
    def show_art_recipe(self, file_path, rgb_dict=None, blocks_list=None):
        if blocks_list is not None:
            rgb_dict = {k: v for k, v in rgb_dict.items() if k in blocks_list}
        elif rgb_dict is None:
            rgb_dict = self.weighted_average_dict
        file_prefix = file_path.split('/')[-1].split('.')[0]
        text_html_str, image_html_str, rows_list = self.get_it_markup(file_path, rgb_dict, file_prefix)
        display(HTML(text_html_str))
        html_path = os.path.abspath(f'../saves/html/{file_prefix}.html')
        os.makedirs(name=os.path.dirname(html_path), exist_ok=True)
        Path(html_path).touch()
        _, _, _, code = traceback.extract_stack()[-2]
        with open(html_path, 'w') as f:
            f.write(f'<html><head><title>{code}</title></head><body>')
            f.write(image_html_str)
            f.write('</body></html>')
        block_names_df = pd.DataFrame(rows_list)
        if blocks_list is not None:
            mask_series = block_names_df.block_name.isin([self.get_block_name(file_name) for file_name in blocks_list])
            block_names_df = block_names_df[mask_series]
        block_names_series = block_names_df.block_name.value_counts()
        stacks_list = []
        block_names_list = []
        for block_name, block_count in block_names_series.iteritems():
            stacks_list, summary_str = self.get_stack_summary(block_count, block_name, stacks_list)
            print(summary_str)
            block_names_list.append(block_name)
        print()
        for stack_count, blocks_list in self.collate(stacks_list):
            stack_collation = self.get_stack_collation(blocks_list, stack_count)
            print(stack_collation)
        webbrowser.open(html_path, new=2)
        
        return block_names_df
    
    
    
    def get_next_recipe(self, file_path='../saves/png/visual_construction101x101.png'):
        block_names_df = self.show_art_recipe(file_path, rgb_dict=self.dominant_dict, blocks_list=self.unpowdered_and_unglazed_list+self.stained_glass_list)
        
        return block_names_df
    
    
    
    def get_file_names_dataframe(self, file_path, rgb_dict):
        img_array = np.array(Image.open(file_path))
        row_count = img_array.shape[0]
        col_count = img_array.shape[1]
        rows_list = []
        for row in range(row_count):
            for col in range(col_count):
                row_dict = {}
                row_dict['row_number'] = row
                row_dict['column_number'] = col
                
                file_name = self.pixel_to_filename(img_array, row, col, rgb_dict)
                row_dict['file_name'] = file_name
                
                block_name = self.get_block_name(file_name)
                row_dict['block_name'] = block_name
                
                hex_str = self.get_hex_str(rgb_dict, file_name)
                row_dict['hex_str'] = hex_str
                
                rows_list.append(row_dict)
        file_names_df = pd.DataFrame(rows_list)
        
        return file_names_df
    
    
    
    def get_next_file_names_dataframe(self, file_path='../saves/png/visual_construction101x101.png'):
        blocks_list = self.unpowdered_and_unglazed_list + self.stained_glass_list
        rgb_dict = {k: v for k, v in self.dominant_dict.items() if k in blocks_list}
        file_names_df = self.get_file_names_dataframe(file_path, rgb_dict)
        
        return file_names_df
    
    
    
    def group_list(self, l, group_size):
        """
        :param l:           list
        :param group_size:  size of each group
        :return:            Yields successive group-sized lists from l.
        """
        for i in range(0, len(l), group_size):
            yield l[i:i+group_size]
    
    
    
    def get_section_file_path(self, art_file_path, row_range, column_range):
        art_img = Image.open(art_file_path)
        left = column_range.start
        top = row_range.start
        right = column_range.stop
        bottom = row_range.stop
        cropped_img = art_img.crop((left, top, right, bottom))
        art_dir = os.path.dirname(art_file_path)
        art_file_name = art_file_path.split(os.sep)[-1].split('.')[0]
        section_file_name = f'{art_file_name}_{left}_{top}_{right}_{bottom}.png'
        section_file_path = os.path.join(art_dir, section_file_name)
        cropped_img.save(os.path.abspath(section_file_path))
        
        return section_file_path
    
    
    
    def convert_minecraft_coords_to_rowcols(self, x, z):
        col = x + 495
        row = z - 207
        
        return row, col
    
    
    
    def convert_minecraft_coords_to_gimp_coords(self, x, z):
        row = x + 495
        col = z - 207
        
        return row, col
    
    
    
    def get_text_html_by_section(self, file_names_df, row_range, column_range, middle_row=None, center_column=None):
        text_html_str = '<table style="border-collapse:collapse;">'
        for row in row_range:
            text_html_str += '<tr>'
            for col in column_range:
                mask_series = (file_names_df.row_number == row) & (file_names_df.column_number == col)
                attributes_dict = file_names_df[mask_series].to_dict(orient='records')[0]
                block_name = attributes_dict['block_name']
                hex_str = attributes_dict['hex_str']
                x, z = self.convert_rowcols_to_minecraft_coords(row, col)
                td_style = f'background-color:{hex_str};text-align:center;'
                if (middle_row is not None) and (center_column is not None) and (row == middle_row) and (col == center_column):
                    td_style += 'border:1px solid white;'
                text_html_str += f'<td title="X:{x} Z:{z}" style="{td_style}" width="10px">{block_name}</td>'
            text_html_str += '</tr>'
        text_html_str += '</table><hr />'
        
        return text_html_str
    
    
    
    def display_next_minimap(self, x=-450, z=233, art_file_path='../saves/png/visual_construction101x101.png', file_names_df=None):
        if file_names_df is None:
            file_names_df = self.get_next_file_names_dataframe(art_file_path)
        middle_row, center_column = self.convert_minecraft_coords_to_rowcols(x, z)
        row_range = range(middle_row-5, middle_row+6)
        column_range = range(center_column-5, center_column+6)
        text_html_str = self.get_text_html_by_section(file_names_df, row_range, column_range, middle_row=middle_row, center_column=center_column)
        display(HTML(text_html_str))
    
    
    
    def get_image_html_by_section(self, art_file_path, file_names_df, row_range, column_range):
        td_style = 'padding:0;margin:0;'
        img_style = 'display:block;margin:0!important;padding:0!important;border:0!important;'
        image_html_str = '<table style="border-collapse:collapse;">'
        is_first_row = True
        for row in row_range:
            image_html_str += '<tr>'
            for col in column_range:
                mask_series = (file_names_df.row_number == row) & (file_names_df.column_number == col)
                attributes_dict = file_names_df[mask_series].to_dict(orient='records')[0]
                file_name = attributes_dict['file_name']
                img_path = os.path.abspath(f'{self.textures_dir}/{file_name}')
                block_name = attributes_dict['block_name']
                x, z = self.convert_rowcols_to_minecraft_coords(row, col)
                image_html_str += f'<td title="X:{x} Z:{z} {block_name}" style="{td_style}">'
                image_html_str += f'<img src="file:///{img_path}" style="{img_style}" /></td>'
            if is_first_row:
                
                # Computing the first row values only once
                left = column_range.start
                top = row_range.start
                right = column_range.stop
                bottom = row_range.stop
                section_file_path = self.get_section_file_path(art_file_path, row_range, column_range)
                section_file_name = art_file_path.split('/')[-1].split('.')[0]
                src_url = 'file:///' + os.path.abspath(section_file_path).replace(os.sep, '/')
                image_td_style = f"{td_style}background-image:url('{src_url}');background-size:cover;"
                image_td_style += 'background-position:center;'
                
                image_html_str += f'<td title="{section_file_name} Left: {left} Top: {top} Right: {right} Bottom: {bottom}" style="{image_td_style}" rowspan={len(row_range)} '
                image_html_str += f'width="{len(column_range)*16}px"></td>'
                is_first_row = False
            image_html_str += '</tr>'
        image_html_str += '</table>'
        
        return image_html_str
    
    
    
    def surf_to_next_minimap(self, x=-450, z=233, art_file_path='../saves/png/visual_construction101x101.png', file_names_df=None):
        if file_names_df is None:
            file_names_df = self.get_next_file_names_dataframe(art_file_path)
        row, col = self.convert_minecraft_coords_to_rowcols(x, z)
        row_range = range(row-5, row+5)
        column_range = range(col-5, col+5)
        image_html_str = self.get_image_html_by_section(art_file_path, file_names_df, row_range, column_range)
        section_dir = '../saves/html'
        section_file_name = art_file_path.split('/')[-1].split('.')[0]
        left = column_range.start
        top = row_range.start
        right = column_range.stop
        bottom = row_range.stop
        section_file_name = f'{section_file_name}_{left}_{top}_{right}_{bottom}.html'
        section_file_path = os.path.join(section_dir, section_file_name)
        Path(section_file_path).touch()
        with open(section_file_path, 'w') as f:
            f.write(f'<html><head><title>{section_file_name} Left: {left} Top: {top} Right: {right} Bottom: {bottom}</title></head><body>')
            f.write(image_html_str)
            f.write('</body></html>')
        webbrowser.open(section_file_path, new=2)
    
    
    
    def get_it_markup_by_groups(self, art_file_path, file_names_df, row_groups_list=None, column_groups_list=None):
        if row_groups_list is None:
            row_groups_list = list(self.group_list(range(file_names_df.row_number.min(), file_names_df.row_number.max()+1), 10))
        if column_groups_list is None:
            column_groups_list = list(self.group_list(range(file_names_df.column_number.min(), file_names_df.column_number.max()+1), 10))
        tuples_list = []
        for row_range in row_groups_list:
            for column_range in column_groups_list:
                text_html_str = self.get_text_html_by_section(file_names_df, row_range, column_range)
                image_html_str = self.get_image_html_by_section(art_file_path, file_names_df, row_range, column_range)
                tuples_list.append(text_html_str, image_html_str)
        
        return tuples_list
    
    
    
    def get_map_center(self, file_path='../saves/png/visual_construction101x101.png', file_name='cyan_terracotta.png'):
        file_names_df = self.get_next_file_names_dataframe(file_path=file_path)
        mask_series = (file_names_df.file_name == file_name)
        
        mean_row_number = file_names_df[mask_series].row_number.mean()
        file_names_df['middleness'] = file_names_df.row_number.map(lambda x: abs(x - mean_row_number))
        
        mean_column_number = file_names_df[mask_series].column_number.mean()
        file_names_df['centerness'] = file_names_df.column_number.map(lambda x: abs(x - mean_column_number))
        
        return file_names_df[mask_series].sort_values(['middleness', 'centerness'])
    
    
    
    def get_circular_edge_set(self, X=51, Y=51, r=11):
        M = 100
        angle = np.exp(1j * 2 * np.pi / M)
        angles = np.cumprod(np.ones(M + 1) * angle)
        x, y = np.real(angles), np.imag(angles)
        edge_set = set()
        for x_y_tuple in zip([int(point_x) for point_x in X + r * x], [int(point_y) for point_y in Y + r * y]):
            edge_set.add(x_y_tuple)
        
        return edge_set
    
    
    
    def show_columns_in_circle(self, diameter=21):
        radius = diameter / 2
        if (diameter % 2) == 0:
            maxblocks = math.ceil(radius - .5) * 2 + 1
        else:
            maxblocks = math.ceil(radius) * 2
        for col in range(int(-maxblocks / 2) + 1, int(maxblocks / 2)):
            print(col)
    
    
    
    def distance(self, first_tuple, second_tuple):
        first_row, first_colum = first_tuple
        second_row, second_colum = second_tuple
        row_distance = abs(first_row - second_row)
        column_distance = abs(first_colum - second_colum)
        
        return math.sqrt(row_distance**2 + column_distance**2)
    
    
    
    def get_filename(self, row, col):
        mask_series = (file_names_df.row_number == row) & (file_names_df.column_number == col)
        file_name = file_names_df[mask_series].file_name.squeeze()
        
        return file_name
    
    
    
    def get_circle_html(self, middle_row, center_column, diameter):
        radius = diameter / 2
        if (diameter % 2) == 0:
            maxblocks = math.ceil(radius - .5) * 2 + 1
        else:
            maxblocks = math.ceil(radius) * 2
        west_column = north_row = middle_center - diameter
        east_column = south_row = middle_center + diameter
        td_style = 'padding:0;margin:0;'
        img_style = 'display:block;margin:0!important;padding:0!important;border:0!important;'
        html_str = '<table style="border-collapse:collapse;">'
        for row in range(int(-maxblocks / 2) + 1, int(maxblocks / 2)):
            html_str += '<tr>'
            for col in range(int(-maxblocks / 2) + 1, int(maxblocks / 2)):
                file_name = self.get_filename(middle_row+row, center_column+col)
                block_name = self.get_block_name(file_name)
                html_str += f'<td title="{block_name}" style="{td_style}">'
                if self.distance((middle_row, center_column), (middle_row+row, center_column+col)) <= radius:
                    img_path = os.path.abspath(os.path.join(self.textures_dir, file_name))
                    html_str += f'<img src="file:///{img_path}" style="{img_style}" /></td>'
                else:
                    html_str += '</td>'
            html_str += '</tr>'
        html_str += '</table>'
        
        return html_str
    
    
    
    def surf_to_next_circle_html(self, middle_center=51, diameter=21):
        html_str = self.get_circle_html(middle_center, middle_center, diameter)
        html_path = os.path.abspath(f'../saves/html/tens.html')
        os.makedirs(name=os.path.dirname(html_path), exist_ok=True)
        Path(html_path).touch()
        with open(html_path, 'w') as f:
            f.write(f'<html><head><title>Tens</title></head><body>')
            f.write(html_str)
            f.write('</body></html>')
        webbrowser.open(html_path, new=2)