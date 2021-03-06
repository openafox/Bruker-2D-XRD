#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Opens Bruker RAW V3, 2D and 3D Data and stores in nice format - based on
"General Area Detector Diffraction System (GADDS) Version 4.1.xx"
Apendix B. and https://github.com/wojdyr/xylib"""
# Copyright 2015 Austin Fox
# Program is distributed under the terms of the
# GNU General Public License see ./License for more information.

# Python 3 compatibility
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import (
         bytes, dict, int, list, object, range, str,
         ascii, chr, hex, input, next, oct, open,
         pow, round, super,
         filter, map, zip)
# #######################

import sys, os
import numpy as np
import struct


class BrukerHeader(object):
    """Bruker Raw Header Dictonary"""

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:

        self._attrs = {
            'version':       [None, 'Version',                     8,   0],
            'file_status':   [None, 'File Status',              '<I',   8],
            'range_cnt':     [None, 'Range Count',              '<I',  12],
            'm_date':        [None, 'Measure Date',               10,  16],
            'm_time':        [None, 'Measure Time',               10,  26],
            'user':          [None, 'User',                       72,  36],
            'site':          [None, 'Site',                      218, 108],
            'sample_id':     [None, 'Sample ID',                  60, 326],
            'comment':       [None, 'Comment',                   160, 386],
            'head_2':        [None, 'head 2',                      2, 546],
            'c_goni':        [None, 'Goniometer Model',         '<I', 548],
            'c_goni_s':      [None, 'Goniometer Stage',         '<I', 552],
            'c_samp_l':      [None, 'Sample Changer',           '<I', 556],
            'c_goni_c':      [None, 'Goniometer Controler',     '<I', 560],
            'c_goni_r':      [None, '(R4) goniometer radius',   '<f', 564],
            'fix_divr':      [None, '(R4) fixed divergence',    '<f', 568],
            'fix_samp':      [None, '(R4) fixed sample slit',   '<f', 572],
            'prim_ss':       [None, 'primary Soller slit',      '<I', 576],
            'prim_mon':      [None, 'primary monochromator',    '<I', 580],
            'fix_anti':      [None, '(R4) fixed antiscatter',   '<f', 584],
            'fix_detc':      [None, '(R4) fixed detector slit', '<f', 588],
            'sec_ss':        [None, 'secondary Soller slit',    '<f', 592],
            'fix_tf':        [None, 'fixed thin film attach',   '<I', 596],
            'beta_f':        [None, 'beta filter',                 4, 600],
            'sec_mon':       [None, 'secondary monochromator',  '<f', 604],
            'anode':         [None, 'Anode Material',              4, 608],
            'head_3':        [None, 'head 3',                      4, 612],
            'alpha_ave':     [None, 'Alpha Average',            '<d', 616],
            'alpha_1':       [None, 'Alpha 1',                  '<d', 624],
            'alpha_2':       [None, 'Alpha 2',                  '<d', 632],
            'beta':          [None, 'Beta',                     '<d', 640],
            'alpha_ratio':   [None, 'Alpha_ratio',              '<d', 648],
            'unit_nm':       [None, '(C4) Unit Name',              4, 656],
            'int_beta_a1':   [None, 'Intensity Beta:a1',           4, 660],
            'mea_time':      [None, 'Measurement Time',         '<f', 664],
            'head_4':        [None, 'head 4',                     43, 668],
            'hard_dep':      [None, 'hard_dep',                    1, 711],
            }

    def pos(self, key):
        """return file position of a key"""
        if key in self._attrs:
            return self._attrs[key][3]
        return None

    def typ(self, key):
        """return file type of a key"""
        if key in self._attrs:
            return self._attrs[key][2]
        return None

    def label(self, key):
        """return file type of a key"""
        if key in self._attrs:
            return self._attrs[key][1]
        return None

    def __getitem__(self, key):
        if key in self._attrs:
            return self._attrs[key][0]
        return None

    def __len__(self):
        return len(self._attrs)

    def __setitem__(self, key, item):
        if key in self._attrs:
            self._attrs[key][0] = item
        else:
            self._attrs[key] = [item, key, len(self._attrs)]

    def __delitem__(self, key):
        if key in self._attrs:
            del self._attrs[key][0]

    def __iter__(self):
        self.index = -1
        return self

    def __next__(self):
        # Get items sorted in specified order:
        keys = sorted(self._attrs, key=lambda key: self._attrs[key][3])
        if self.index == len(keys) - 1:
            raise StopIteration
        self.index = self.index + 1
        key = keys[self.index]
        return key

    def __str__(self):
        """def what prints out
        https://stackoverflow.com/questions/1436703/difference-between-str-and-repr-in-python/2626364#2626364
        """
        out = ('{' +
               '\n'.join('{:^20s}{:^20s}'.format(key, str(self._attrs[key][0]))
               for key in self._attrs) + '}')
        return out

    def copy(self):
        """.copy() should always be a deepcopy."""
        return self.__deepcopy__(None)

    def __copy__(self):
        """.copy() should always be a deepcopy."""
        return self.__deepcopy__(None)

    def __deepcopy__(self, memo):
        """.deepcopy()"""
        _head = BrukerHeader()
        _head._attrs = self._attrs
        return _head

    def __add__(self, other):
        try:
            # check if any keys overlap and raise exception if they do
            same = [key for key in self._attrs if key in other._attrs]
            if same:
                raise Exception('%s is in all header types')
        except:
            raise Exception('Type mismatch, must be BrukerHeader')

        _head = self.copy()
        _head._attrs.update(other._attrs)
        return _head


class BrukerRangeHeader(BrukerHeader):
    """Bruker Raw Header Dictonary"""

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:

        self._attrs = {
            'header_len':    [None, 'Header Len',               '<I',   0],
            'steps':         [None, 'Steps',                    '<I',   4],
            'start_theta':   [None, 'Start Theta',              '<d',   8],
            'start_2th':     [0,    'Start 2Theta',             '<d',  16],
            'drive_chi':     [0,    'Chi Start',                '<d',  24],
            'drive_phi':     [None, 'Phi Start',                '<d',  32],
            'drive_x':       [None, 'X Start',                  '<d',  40],
            'drive_y':       [None, 'Y Start',                  '<d',  48],
            'drive_z':       [None, 'Z Start',                  '<d',  56],
            'ig_1':          [None, 'ig 1',                     '<Q',  64],
            'ig_2':          [None, 'ig 2',                        6,  72],
            'ig_2_1':        [None, 'ig 2_1',                   '<h',  78],
            'R8':            [None, '(R8) variable anitscat',   '<d',  80],
            'ig_3':          [None, 'ig 3',                        6,  88],
            'ig_3_1':        [None, 'ig 3_1',                   '<h',  94],
            'dec_code':      [None, 'Detector',                 '<I',  96],
            'hv':            [None, 'High Voltage',             '<f', 100],
            'amp_gain':      [None, 'Ampliphier Gain',          '<f', 104],
            'dis1_LL':       [None, 'Discriminator1 Lower Lev', '<f', 112],
            'ig_4':          [None, 'ig 4',                     '<I', 116],
            'ig_5':          [None, 'ig 5',                     '<d', 120],
            'ig_6':          [None, 'ig 6',                     '<f', 128],
            'ig_a':          [None, 'ig a',                     '<f', 132],
            'ig_b':          [None, 'ig b',                        5, 136],
            'ig_b_1':        [None, 'ig b_1',                      3, 141],
            'ig_c':          [None, 'Aux Axis 1 start',         '<d', 144],
            'ig_d':          [None, 'Aux Axis 2 start',         '<d', 152],
            'ig_e':          [None, 'Aux Axis 3 start',         '<d', 160],
            'ig_f':          [None, 'Scan Mode',                   4, 168],
            'ig_g':          [None, 'ig g',                     '<I', 172],
            'ig_h':          [None, 'ig h',                     '<I', 172],
            'step_size':     [None, 'Step Size',                '<d', 176],
            'ig_i':          [None, 'ig i',                     '<d', 184],
            'step_time':     [None, 'Time Per Step',            '<f', 192],
            'ig_j':          [None, 'Scan Type',                '<I', 196],
            'ig_k':          [None, 'Delay Time',               '<f', 200],
            'ig_l':          [None, 'ig l',                     '<I', 204],
            'rot_speed':     [None, 'Rotation Speed',           '<f', 208],
            'ig_m':          [None, 'ig m',                     '<f', 212],
            'ig_n':          [None, 'ig n',                     '<I', 216],
            'ig_o':          [None, 'ig o',                     '<I', 220],
            'gen_v':         [None, 'Generator Voltage',        '<I', 224],
            'gen_a':         [None, 'Generator Current',        '<I', 228],
            'ig_p':          [None, 'ig p',                     '<I', 232],
            'ig_q':          [None, 'ig q',                     '<I', 236],
            'lambda':        [None, 'Lambda',                   '<d', 240],
            'ig_r':          [None, 'ig r',                     '<I', 248],
            'ig_s':          [None, 'Len of each data in bits', '<I', 252],
            'sup_len':       [None, 'supplementary header len', '<I', 256],
            'ig_t':          [None, 'ig t',                     '<I', 260],
            'ig_u':          [None, 'ig u',                     '<I', 264],
            'ig_v':          [None, 'ig v',                     '<I', 268],
            'ig_w':          [None, 'ig w',                     '<I', 272],
            'ig_x':          [None, 'Reserved for expansion',   '<I', 280],
            }


class BrukerSupp200(BrukerHeader):
    """Bruker Raw Area Detector Supplemental Header Dictonary"""

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:
        self._attrs = {
            'type':          [None, 'Record type',              '<I',   0],
            'length':        [None, 'record length',            '<I',   4],
            'reserved':      [None, 'reserved',                 '<I',   8],
            'int_start':     [None, 'integration range start',  '<f',  16],
            'int_end':       [None, 'integration range end',    '<f',  20],
            'chi_start':     [None, 'int range chi start',      '<f',  24],
            'chi_end':       [None, 'int range chi end',        '<f',  28],
            'norm':          [None, 'Normalization method',     '<I',  32],
            'prog':          [None, 'program name',               20,  36],
            'act_2th':       [None, 'act 2th',                  '<f',  56],
            'act_omega':     [None, 'act omega',                '<f',  60],
            'act_phi':       [None, 'act phi',                  '<f',  64],
            'act_psi':       [None, 'act psi',                  '<f',  68],
            }


class BrukerSupp190(BrukerHeader):
    """Bruker Raw EVA Supplemental Header Dictonary"""

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:
        self._attrs = {
            'type':          [None, 'Record type',              '<I',   0],
            'length':        [None, 'record length',            '<I',   4],
            '2th_off':       [None, '2theta offset [deg]',      '<f',   8],
            'int_off':       [None, 'intensity offset [% max]', '<f',  12],
            'ig_z':          [None, 'reserved for expansion',     16,  16],
            }



class BrukerSupp150(BrukerHeader):
    """Bruker Raw removed data for search Supplemental Header Dictonary"""

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:
        self._attrs = {
            'type':          [None, 'Record type',              '<I',   0],
            'length':        [None, 'record length',            '<I',   4],
            'ex_start':      [None, 'excld 2theta start [deg]', '<f',   8],
            'ex_end':        [None, 'excld 2theta end [deg]',   '<f',  12],
            'ig_z':          [None, 'reserved for expansion',     16,  16],
            }


class BrukerSupp140(BrukerHeader):
    """Bruker Raw Comment Supplemental Header Dictonary"""
    #Need to fig out how to handle variable length

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:
        self._attrs = {
            'type':          [None, 'Record type',              '<I',   0],
            'length':        [None, 'record length',            '<I',   4],
            'comment':       [None, 'comment',                  '??',   8],
            }


class BrukerSupp130(BrukerHeader):
    """Bruker Raw QCI parameters (obsolete) Supplemental Header Dictonary"""
    #Need to fig out how to handle variable length

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:
        self._attrs = {
            'type':          [None, 'Record type',              '<I',   0],
            'length':        [None, 'record length',            '<I',   4],
            'var_type':      [None, 'variable type',            '<f',   8],
            'comp_name':     [None, 'ASCII:compound name',      '??',  12],
            }


class BrukerSupp120(BrukerHeader):
    """Bruker Raw Description for Optimized Quantitative Measurement
    record Supplemental Header Dictonary"""

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:
        self._attrs = {
            'type':          [None, 'Record type',              '<I',   0],
            'length':        [None, 'record length',            '<I',   4],
            'ig_z':          [None, 'undefined',                  64,   8],
            }


class BrukerSupp110(BrukerHeader):
    """Bruker Raw PSD parameters Supplemental Header Dictonary"""

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:
        self._attrs = {
            'type':          [None, 'Record type',              '<I',   0],
            'length':        [None, 'record length',            '<I',   4],
            'goni_2th':      [None, '2theta of goni[deg]',      '<f',   8],
            'chnl':          [None, 'first channel used',       '<I',  16],
            'ig_z':          [None, 'reserved for expansion',     20,  20],
            }


class BrukerSupp100(BrukerHeader):
    """Bruker Raw Oscillation parameters Supplemental Header Dictonary"""

    def __init__(self):
        # For each metta data set keywords are contain (1) the actual
        # value, (2) a user-suitable label for the item, (3) the data type
        # and (4) the data position in the group:
        # ordering index:
        self._attrs = {
            'type':          [None, 'Record type',              '<I',   0],
            'length':        [None, 'record length',            '<I',   4],
            'osc_drv':       [None, 'oscillation drive',        '<f',   8],
            'osc_amp':       [None, 'oscil amp[deg or mm]',     '<d',  16],
            'osc_spd':       [None, 'oscil spd[deg/s or mm/s]', '<f',  24],
            'ig_z':          [None, 'reserved for expansion',     12,  28],
            }


class BrukerRange(object):

    def __init__(self):
        self.metta = {}
        self.supmetta = {}
        self.counts_data = []


class BrukerData(object):
    """Retrieves and stores Bruker XRD Data"""

    def __init__(self, filename=None):
        self.filename = filename
        self.rngs = []
        if filename:
            self.filecontent = self.get_data_from_file(self.filename)
            self.header = self.get_metta(BrukerHeader(), 0)
            pos = 712
            for i in range(self.header['range_cnt']):
                rng, pos = self.get_range(pos)
                if rng.metta['steps'] > 0:
                    self.add_range(rng)
                else:
                    self.header['range_cnt'] -= 1
                    print('ERROR (Databruker)!! - Missing range %d' % i)

            if self.rngs[0].supmetta['type'] == 200:  # Area map
                self.x = []
                self.y = []
                self.get_smap()
            else:
                self.smap = None

                # need to generalize this as func then add to get smap below
                #assuming all rngs are of same len
                self.y = self.rngs[0].counts_data
                twoth_0 = self.rngs[0].metta['start_2th']
                twoth_s = self.rngs[0].metta['step_size']
                twoth_e = twoth_0 + twoth_s*self.rngs[0].metta['steps']
                twoth_len = len(self.y)
                self.x = np.linspace(twoth_0, twoth_e, twoth_len)
                #raise Exception("not file from area detector, this is "
                #                "currently not supported. Sorry")
        else:
            self.header = None
            self.x = []
            self.y = []
            self.smap = np.array([[]])

    def add_range(self, rng):
        self.rngs.append(rng)

    def get_data_from_file(self, filename):
        try:
            with open(filename, mode='rb') as f:  # b is important -> binary
                filecontent = f.read()
        except IOError as e:
            raise Exception("I/O error({0}): {1}".format(e.errno, e.strerror))

        if b"RAW1.01" not in filecontent[0:8]:
            raise Exception("invalid file type must be RAW1.01")
            #add other versions and gfrm
        return filecontent

    def get_range(self, pos):
        rng = BrukerRange()
        rng.metta = self.get_metta(BrukerRangeHeader(), pos)
        pos += rng.metta['header_len']
        rng.counts_data = []
        if rng.metta['sup_len'] > 0:
            (typ, ) = struct.unpack('<I', self.filecontent[pos: pos+4])
            ##print(pos, 'typ', typ)
            # use proper suppclass
            rng.supmetta = self.get_metta(globals()["BrukerSupp"+ str(typ)](), pos)
        else:
            rng.supmetta = {'type': None,}

        pos += rng.metta['sup_len']
        data_len = rng.metta['steps']
        for i in range(data_len):
            (ret,) = struct.unpack('<f', self.filecontent[pos+i*4: pos+i*4+4])
            rng.counts_data.append(ret)
        ##print(pos, 'ret', ret)
        pos += data_len * 4
        return rng, pos

    def get_smap(self):
        y = []
        smap = []

        for i, rng in enumerate(self.rngs):
            phi = rng.supmetta['act_psi']
            chi_s = rng.supmetta['chi_start']
            chi_e = rng.supmetta['chi_end']
            y.append(90 - phi +
                     (90+chi_s-(chi_s-chi_e)/2))

            # print(phi, chi_s, chi_e, y[i])
            smap.append(rng.counts_data)
        # Sadly must handel silyness of bruker not keeping ranges same length
        # https://stackoverflow.com/questions/27890052/convert-and-pad-a-list-to-numpy-array
        lens = np.array([len(item) for item in smap])
        mask = lens[:, None] > np.arange(lens.max())
        # print(mask.shape)
        out = np.full(mask.shape, 0)
        out[mask] = np.concatenate(smap)

        userng = np.argmax(lens)
        twoth_0 = self.rngs[userng].metta['start_2th']
        twoth_s = self.rngs[userng].metta['step_size']
        twoth_e = twoth_0 + twoth_s*self.rngs[userng].metta['steps']
        twoth_len = lens.max()
        self.x = np.linspace(twoth_0, twoth_e, twoth_len)
        self.y = np.linspace(min(y), max(y), len(self.rngs))
        # convert smap to np.array
        self.smap = np.asarray(out)
        # print(self.x.shape, self.y.shape, self.smap.shape)

    def get_real_xy(self, x=None, y=None):
        out = [None, None]
        for i, z in enumerate(['x', 'y']):
            if isinstance(locals()[z], list):
                out[i] = [getattr(self, z)[int(i)] for i in locals()[z]]
            elif isinstance(locals()[z], (int, float)):
                out[i] = getattr(self, z)[int(locals()[z])]

        return out

    def get_index_xy(self, x, y):
        """Assumes x and y are ordered arrays with len > 0"""
        y_out = np.abs(self.y-y).argmin()
        if len(self.y) == 1 and y > self.y[0]:
            y_out = 1
        x_out = np.abs(self.x-x).argmin()
        if len(self.x) == 1 and x > self.x[0]:
            x_out = 1
        return x_out, y_out

    def integrate_2d(self, area='all', axis='x'):
        """ area - (x1, y1, x2, y2)
            axis - axis to preserve"""
        if area == 'all':
            x1 = 0
            y1 = 0
            (y2, x2) = self.smap.shape
        elif len(area) != 4:
            raise Exception('area must be "all" or (x1, y1, x2, y2).')
        else:
            x1, y1, x2, y2 = area

        if axis == 'x':
            line = np.sum(self.smap[y1:y2, x1:x2], axis=0)  # 2th
        elif axis == 'y':
            line = np.sum(self.smap[y1:y2, x1:x2], axis=1)  # psi
        else:
            raise Exception('axis must be specified either "x" or "y".')
        return line

    def _unpack(self, filecontent, pos, typ, bits):
        if isinstance(typ, int):
            typ = str(typ) + 's'
        (out,) = struct.unpack(typ, filecontent[pos: pos + bits])
        if isinstance(out, (str, bytes)):
            out = out.strip(b'\x00').strip()
        return out

    def get_metta(self, mettaclass, start_pos):

        for key in mettaclass:
            pos = mettaclass.pos(key)+start_pos
            typ = mettaclass.typ(key)
            bits = 0
            if isinstance(typ, int):
                bits = typ
            elif typ == '<h' or typ == '<H':
                bits = 2
            elif typ == '<f' or typ == '<I':
                bits = 4
            elif typ == '<d' or typ == '<Q' or typ == '<q':
                bits = 8
            elif typ == '??':
                bits = int(mettaclass['length'] - pos)
                typ = bits

            mettaclass[key] = self._unpack(self.filecontent, pos, typ, bits)
            ##print(pos - 712, key, mettaclass[key])
        return mettaclass

    def __add__(self, other):
        try:
            if not np.array_equal(self.y, other.y):
                raise Exception('Must have same y scale')
        except:
            raise Exception('Type mismatch, must be BrukerData')
        ret = BrukerData()
        ret.y = self.y
        ret.smap = np.concatenate((self.smap, other.smap), axis=1)
        ret.x = np.concatenate((self.x, other.x), axis=0)
        ret.rngs = self.rngs + other.rngs
        ret.filename = self.filename + " & " + other.filename

        return ret

    # def __radd__(self, other):


if __name__ == '__main__':
    print("test")
    if False:
        test = BrukerHeader()
        for key in test:
            print(test.label(key), test.pos(key), test.typ(key))
    if True:
        print("test")
        #data = BrukerData('/mnt/W/Austin_Fox/XRD/5582_map.raw')
        data = BrukerData('/mnt/W/Austin_Fox/XRD/5582.raw')
        print(data)
