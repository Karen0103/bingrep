# BinGrep, version 1.0.0
# Copyright 2017 Hiroki Hada
# coding:UTF-8

import sys, os, time, argparse
import re
import pprint
#import pydot
import math
import cPickle
import ged_node
from idautils import *
from idc import *
import idaapi

def idascript_exit(code=0):
    idc.Exit(code)

def get_short_function_name(function):
    return function.replace("?", "")[:100]

def mkdir(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)

def cPickle_dump(filename, data):
    with open(filename, "wb") as f:
        cPickle.dump(data, f)

def print_cfg(cfg):
    for block in cfg:
        print "[%02d]" % block.id,
        print hex(block.startEA),

        succs = list(block.succs())
        print "(succs(%d): " % len(succs),

        for i in range(len(succs)):
            sys.stdout.write(hex(succs[i].startEA))

            if i < len(succs) - 1:
                sys.stdout.write(", ")

        print ")"

def output_cfg_as_png_rec(g, block, memo):
    functions1, dummy = get_marks(block, 0)
    hashed_label1 = hash_label(functions1)

    label1 = hex(block.startEA) + ("\n%08x" % hashed_label1)
    g.add_node(pydot.Node(label1, fontcolor='#FFFFFF', color='#333399'))

    for b in list(block.succs()):
        functions2, dummy = get_marks(b, 0)
        hashed_label2 = hash_label(functions2)
        label2 = hex(b.startEA) + ("\n%08x" % hashed_label2)

        if b.startEA not in memo:
            memo.append(b.startEA)
            g.add_edge(pydot.Edge(label1, label2, color='#333399', style='bold'))
            output_cfg_as_png_rec(g, b, memo)
        else:
            g.add_edge(pydot.Edge(label1, label2, color='#333399', style='bold, dotted'))

def output_cfg_as_png(cfg, filename, overwrite_flag):
    blocks_src = {}
    blocks_dst = {}
    block = cfg[0]

    f_name = GetFunctionName(block.startEA)

    if not overwrite_flag and os.path.exists(filename):
        return

    g = pydot.Dot(graph_type='digraph', bgcolor="#F0E0FF")
    size = "21"

    g.set_rankdir('TB')
    g.set_size(size)
    g.add_node(pydot.Node('node', shape='ellipse', margin='0.05', fontcolor='#FFFFFF', fontsize=size, color='#333399', style='filled', fontname='Consolas Bold'))
    g.add_node(pydot.Node('edge', color='lightgrey'))

    memo = []
    output_cfg_as_png_rec(g, block, memo)
    g.write_png(filename)


def get_cfg(function_start, function_end):
    f_name = GetFunctionName(function_start)

    cfg = idaapi.FlowChart(idaapi.get_func(function_start))

    return list(cfg)

def get_cfgs():
    cfgs = []

    for ea in Segments():
        functions = list(Functions(SegStart(ea), SegEnd(ea)))
        functions.append(SegEnd(ea))

        for i in range(len(functions) - 1):
            function_start = functions[i]
            function_end   = functions[i+1]
            cfg = get_cfg(function_start, function_end)
            cfgs.append(cfg)

    return cfgs

def hash_label(marks):
    tmp = sorted(set(marks))
    tmp = "".join(tmp)
    tmp = tmp.upper()

    def rot13(string):
        return reduce(lambda h,c: ((h>>13 | h<<19)+ord(c)) & 0xFFFFFFFF, [0]+list(string))

    hashed_label = rot13(tmp)
    hashed_label = hashed_label & 0xFFFFFFFF
    return hashed_label


def get_marks(block, gamma):
    marks = []
    for head in Heads(block.startEA, block.endEA):
        mnem = GetMnem(head)
        opnd = (GetOpnd(head, 0), GetOpnd(head, 1), GetOpnd(head, 2))

        if mnem not in ["call"]:
            for buf in (opnd[1], opnd[2]):
                if buf:
                    match = re.search("([\dA-F]+)h", buf)
                    if match:
                        magic = int(match.group(1), 16)
                        if 0x00001000 <= magic <= 0xffffffff:
                            marks.append(hex(magic))

            for buf in (opnd[0], opnd[1], opnd[2]):
                if buf:
                    match = re.search("offset (a[\S]+)", buf)
                    if match:
                        offset_a = match.group(1)
                        if offset_a[:4] == "asc_": continue
                        marks.append(offset_a)

            continue

        else:
            gamma += 1
            if opnd[0][:4] == "sub_": continue
            if opnd[0][0] in ["?", "$"]: continue
            if opnd[0] in ["eax", "ebx", "ecx", "edx", "esi", "edi"]: continue
            if opnd[0] in ["__SEH_prolog4", "__SEH_epilog4", "__EH_prolog3_catch"]: continue
            if opnd[0].find("cookie") >= 0: continue
            marks.append(opnd[0])
            continue

    return marks, gamma

def get_mnems(block):
    mnems = []

    for head in Heads(block.startEA, block.endEA):
        mnem = GetMnem(head)
        opnd = (GetOpnd(head, 0), GetOpnd(head, 1), GetOpnd(head, 2))
        buf  = " "
        for o in opnd:
            if not o: break
            elif o in ["eax", "ebx", "ecx", "edx", "ax", "bx", "cx", "dx", "al", "bl", "cl", "dl", "ah", "bh", "ch", "dh", "esi", "edi", "si", "di", "esp", "ebp"]:
                buf += "reg "
            elif o[:3] == "xmm":                buf += "reg "
            elif o.find("[") >= 0:              buf += "mem "
            elif o[:6] == "offset":             buf += "off "
            elif o[:4] == "loc_":               buf += "loc "
            elif o[:4] == "sub_":               buf += "sub "
            elif o.isdigit():                   buf += "num "
            elif re.match("[\da-fA-F]+h", o):   buf += "num "
            elif o[:6] == "dword_":             buf += "dwd "
            else:                               buf += "lbl "

        mnems.append(mnem + buf)

    return mnems

def cfg_to_cft_rec(block, memo, abr):
    (alpha, beta, gamma) = abr
    alpha += 1

    marks, gamma    = get_marks(block, gamma)
    hashed_label    = hash_label(marks)
    mnems           = get_mnems(block)
    tree = ged_node.Node(hashed_label)

    for b in list(block.succs()):
        beta += 1
        if b.startEA not in memo:
            memo.append(b.startEA)
            tmp, (alpha, beta, gamma), tmp2 = cfg_to_cft_rec(b, memo, (alpha, beta, gamma))
            tree   = tree.addkid(tmp)
            mnems += tmp2

    return tree, (alpha, beta, gamma), mnems


def cfg_to_cft(cfg):
    block = cfg[0]

    memo = []
    memo.append(block.startEA)

    return cfg_to_cft_rec(block, memo, (0, 0, 0))

def dump_function_info(cfgs, program, function, f_image, f_all, f_overwrite):
    function_num = len(cfgs)
    dump_data_list = {}

    for cfg in cfgs:
        function_name       = GetFunctionName(cfg[0].startEA)
        (cft, abr, mnems)   = cfg_to_cft(cfg)

        dump_data_list[function_name] = {}
        dump_data_list[function_name]["FUNCTION_NAME"]  = function_name
        dump_data_list[function_name]["CFT"]            = cft
        dump_data_list[function_name]["ABR"]            = abr
        dump_data_list[function_name]["MNEMS"]          = mnems

    def dump_pickle(dump_data_list, program, function, f_overwrite):
        function_name_short = get_short_function_name(function)
        filename_pickle     = os.path.join(function_name_short + ".pickle")
        if f_overwrite or not os.path.exists(filename_pickle):
            cPickle_dump(filename_pickle, dump_data_list[function])

    cPickle_dump(program + ".dmp", dump_data_list)


def main(function, f_image, f_all, f_overwrite):

    sys.setrecursionlimit(3000)

    program = idaapi.get_root_filename()
    start_time = time.time()
    cfgs = get_cfgs()
    dump_function_info(cfgs, program, function, f_image, f_all, f_overwrite)
    result_time = time.time() - start_time

    print "Dump finished."
    print "result_time: " + str(result_time) + " sec."


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description="")
    parser.add_argument('-f', dest='function',      default=None, type=str, help='')
    parser.add_argument('-a', dest='f_all',         default=False, action='store_true', help='')
    parser.add_argument('-i', dest='f_image',       default=False, action='store_true', help='Image Flag (Output as PNG)')
    parser.add_argument('-o', dest='f_overwrite',   default=False, action='store_true', help='Overwrite file')
    args = parser.parse_args()

    function        = args.function
    f_image         = args.f_image
    f_all           = args.f_all
    f_overwrite     = args.f_overwrite

    main(function, f_image, f_all, f_overwrite)

    #idascript_exit()



