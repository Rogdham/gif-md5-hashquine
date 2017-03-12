#!/usr/bin/env python2

#
# Copyheart Rogdham, 2017
# See http://copyheart.org/ for more details.
#
# This program is free software. It comes without any warranty, to the extent
# permitted by applicable law. You can redistribute it and/or modify it under
# the terms of the CC0 1.0 Universal Licence (French).
# See https://creativecommons.org/publicdomain/zero/1.0/deed.fr for more
# details.
#

"""
Hashquine generator
"""

import os
import struct
from hashlib import md5

import collide


class Hashquine(object):
    """
    Create a hashquine

    Specify a template directory for background and character images
    """

    def __init__(self, template_dir, out_filename):
        self.template_dir = template_dir
        self.out_filename = out_filename
        self.hash_img_coordinates = (102, 143)
        # read images
        self.background_blocks = self.read_gif('background.gif')
        self.chars_img_data = {}
        for char in '0123456789abcdef':
            blocks = self.read_gif('char_{}.gif'.format(char))
            self.chars_img_data[int(char, 16)] = blocks['img_data']
            width, height = struct.unpack('<HH', blocks['img_descriptor'][5:9])
            if char == '0':
                self.char_width, self.char_height = width, height
            assert (self.char_width, self.char_height) == (width, height)

    def run(self):
        """
        Create and save the hashquine

        Doing so makes sure it works well with Makefiles
        """
        generated_gif = self.generate()
        with open(self.out_filename, 'w') as out_fd:
            out_fd.write(generated_gif)

    def read_gif(self, filename):
        """
        Read the data from the GIF image

        Images must have a specific format: 16-colours pallet, etc.
        """
        blocks = {}
        with open(os.path.join(self.template_dir, filename)) as gif_fd:
            blocks['header'] = gif_fd.read(6)
            assert blocks['header'] in ('GIF87a', 'GIF89a')
            blocks['lcd'] = gif_fd.read(7)  # logical screen descriptor
            assert blocks['lcd'].endswith('\xe3\x10\x00')  # gct of 16 colours
            blocks['gct'] = gif_fd.read(16 * 3)  # global colour table
            blocks['img_descriptor'] = gif_fd.read(10)  # image descriptor
            assert blocks['img_descriptor'][0] == '\x2c'
            assert blocks['img_descriptor'][9] == '\x00'
            # img data
            blocks['img_data'] = gif_fd.read(1)  # LZW min code size
            while True:  # img data sub-blocks
                blocks['img_data'] += gif_fd.read(1)  # sub-block data size
                if blocks['img_data'][-1] == '\x00':
                    break  # final sub-block (size 0)
                blocks['img_data'] += gif_fd.read(ord(blocks['img_data'][-1]))
            assert gif_fd.read(1) == '\x3b'  # trailer
        return blocks

    def generate(self):
        """
        Generate the hashquine
        """
        graphic_control_extension = '\x21\xf9\x04\x04\x02\x00\x00\x00'
        alternatives = {}  # (char_pos, char): (coll_pos, coll)
        # header
        generated_gif = self.background_blocks['header']
        generated_gif += self.background_blocks['lcd']
        generated_gif += self.background_blocks['gct']
        # place comment
        comment = 'Copyheart Rogdham, 2017\n'
        comment += '<3 Copying is an act of love. Please copy and share.\n\n'
        comment += 'Released under the CC0 1.0 universel licence\nSee '
        comment += 'https://creativecommons.org/publicdomain/zero/1.0/deed.fr'
        comment += '\n'
        generated_gif += '\x21\xfe{}{}\x00'.format(chr(len(comment)), comment)
        # place background
        generated_gif += graphic_control_extension
        generated_gif += self.background_blocks['img_descriptor']
        generated_gif += self.background_blocks['img_data']
        # start comment
        generated_gif += '\x21\xfe'
        # generate all possible md5 characters frames
        top, left = self.hash_img_coordinates
        for char_pos in range(32):
            left += self.char_width
            for char in range(16):
                char_img = graphic_control_extension
                char_img += '\x2c{}\x00'.format(struct.pack(  # img descriptor
                    '<HHHH', left, top, self.char_width, self.char_height))
                char_img += self.chars_img_data[char]
                # add comment to align to a md5 block
                coll_diff = collide.COLLISION_LAST_DIFF
                align = 64 - (len(generated_gif) % 64)
                generated_gif += chr(align - 1 + coll_diff)
                generated_gif += '\x00' * (align - 1)  # any char would do
                # generate collision
                while True:
                    print 'Generating collision', char_pos * 16 + char + 1
                    coll_img, coll_nop = collide.collide(generated_gif)
                    assert coll_img[coll_diff] < coll_nop[coll_diff]
                    offset = collide.COLLISION_LEN - coll_diff - 1
                    coll_p_img = ord(coll_img[coll_diff]) - offset
                    coll_p_nop = ord(coll_nop[coll_diff]) - offset
                    pad_len = coll_p_nop - coll_p_img - len(char_img) - 4
                    if coll_p_img >= 0 and pad_len >= 0:
                        break
                    print 'Unsatisfying collision, trying again'
                # push collision
                alternatives[char_pos, char] = (len(generated_gif), coll_img)
                generated_gif += coll_nop
                # continue comment up to image
                generated_gif += '\x00' * coll_p_img  # any char would do
                generated_gif += '\x00'  # end comment
                # add image
                generated_gif += char_img
                # start comment and align with big comment (end of coll_nop)
                generated_gif += '\x21\xfe'
                generated_gif += chr(pad_len)
                generated_gif += '\x00' * pad_len  # any char would do
        # end comment and add GIF trailer
        generated_gif += '\x00\x3b'
        # replace colls to show md5
        print 'Target md5:', md5(generated_gif).hexdigest()
        for char_pos, char in enumerate(md5(generated_gif).hexdigest()):
            coll_pos, coll = alternatives[char_pos, int(char, 16)]
            generated_gif = (
                generated_gif[:coll_pos] + coll +
                generated_gif[coll_pos + len(coll):]
            )
        print 'Final md5: ', md5(generated_gif).hexdigest()
        return generated_gif


if __name__ == '__main__':
    import sys
    Hashquine('template', sys.argv[1]).run()
