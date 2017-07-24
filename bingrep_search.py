# BinGrep, version 1.0.0
# Copyright 2017 Hiroki Hada
# coding:UTF-8

import sys, os, time, argparse
import re
import pprint
import math
import cPickle
import ged, lcs

class Chooser(idaapi.Choose2):
    def __init__(self, title, items, embedded=False):
        idaapi.Choose2.__init__(self, title, [["Rank", 3], ["Function", 30], ["GED", 3], ["LCS", 3], ["Vector", 10]])
        self.items = items

    def OnSelectLine(self, n):
        idc.Jump(idc.LocByName(self.items[n][1]))

    def OnClose(self):
        pass

    def OnGetLine(self, n):
        return self.items[n]

    def OnGetSize(self):
        return len(self.items)

def get_dump_png_path(program):
    return os.path.join("dump_" + program, "png")

def get_short_function_name(function):
    return function.replace("?", "")[:100]

def cfg_distance4(cfg_vector1, cfg_vector2):
    return ged.simple_distance(cfg_vector1, cfg_vector2)

def cfg_distance5(mnems1, mnems2):
    rate = (0.0 - lcs.get_lcs_len(mnems1, mnems2)) / len(mnems1)
    return int(rate * 100)

def read_pickle(filename):
    try:
        with open(filename, "rb") as f:
            return cPickle.load(f)

    except IOError:
        print >>sys.stderr, "File not found: %s" % filename
        return False

def print_results(results, stats, src_program, src_function, dst_program):
    result_time = stats["time"]

    print "Src Program : " + src_program
    print "Src Function: " + src_function
    print "Src Vector:   (%d,%d,%d)" % (stats["src_abr"])
    print "Dest Program: " + dst_program
    print "Function Num: %d" % stats["dst_function_num"]
    print "Search Time : %.2f sec " % result_time

    """
    print "-" * 60
    print "No. Next Dist Dist2:                                 Function Vector"
    for result in results:
        (alpha, beta, gamma) = result["ABR"]
        print "%3i %4i %4d  %4d: %40s (%d,%d,%d)" % (result["RANK"], result["NEXT_RANK"], result["DISTANCE1"], -result["DISTANCE2"], result["FUNCTION_NAME"], alpha, beta, gamma)
    print "-" * 60
    """

    answer_list = []
    for (i, result) in enumerate(results):
        vector = "(%d, %d, %d)" % (result["ABR"])
        answer_list.append([str(i+1).rjust(3), str(result["FUNCTION_NAME"]).rjust(3), str(result["DISTANCE1"]).rjust(3), str(-result["DISTANCE2"]), vector])

    chooser = Chooser("Search Results", answer_list)
    chooser.Show()

    sys.stdout.flush()


def print_results_html(results, stats, src_program, src_function, dst_program):
    result_time = stats["time"]
    report_filename = "report_%s_%s_%s.html" % (src_program, src_function, dst_program)

    buf  = """
<html><head>
<title>Report</title>
<style>
body     { margin: 30px; background-color: #F8F8FF; }
h1       { color: #222266; }
table    { border-collapse: collapse; border: solid 0px #000000; }
table.b  { border-collapse: collapse; }
td       { border: solid 1px #000000; padding: 0px 10px 0px 10px; }
td.nb    { border: solid 0px #000000; }
tr.title { background-color: #DDDDFF; font-weight: bold; color: #222266; }
tr.min   { background-color: #FFF0FF; font-weight: bold; color: #882266; }
td.title { background-color: #DDDDFF; font-weight: bold; color: #222266; }
td.img   { background-color: #F0E0FF; text-align: center; }
</style>
</head>
<body>
"""

    buf += "<h1>Search Result</h1>"
    buf += "<table><tr><td class='nb'>"
    buf += "<table class='b'>"
    buf += "<tr><td class='title'>Src Program</td><td>%s</td></tr>\n" % src_program
    buf += "<tr><td class='title'>Src Function</td><td>%s</td></tr>\n" % src_function
    buf += "<tr><td class='title'>Src Function Vector</td><td>(%d,%d,%d)</td></tr>\n" % stats["src_abr"]
    buf += "<tr><td class='title'>Dst Program</td><td>%s</td></tr>\n" % dst_program
    buf += "<tr><td class='title'>Dst Function</td><td>%d</td></tr>\n" % stats["dst_function_num"]
    buf += "<tr><td class='title'>Search Time</td><td>%.2f sec</td></tr>\n" % result_time
    buf += "</table>"
    buf += "</td><td class='nb'>"

    imgpath = os.path.join(get_dump_png_path(src_program), src_function + ".png")

    buf += "<br><a href='%s'><img src='%s' style='max-height:100px'></a><br><br>" % (imgpath, imgpath)
    buf += "</td></tr>"
    buf += "</table><br>"
    buf += "<table class='b'><tr class='title'><td>Rank</td><td>Next</td><td>Dist.</td><td>Function</td><td>Vector</td><td>Image</td></tr>"

    min_distance = results[0]["DISTANCE1"]

    for result in results:
        if result["DISTANCE1"] == min_distance: min_flag = " class='min'"
        else: min_flag = ""

        (alpha, beta, gamma) = result["ABR"]

        buf += "<tr%s><td>%d</td><td>%d</td><td>%d</td><td>%s</td><td>(%d,%d,%d)</td>" % (min_flag, result["RANK"], result["NEXT_RANK"], result["DISTANCE1"], result["FUNCTION_NAME"], alpha, beta, gamma)

        imgpath = os.path.join(get_dump_png_path(dst_program), result["FUNCTION_NAME"] + ".png")

        if os.path.exists(imgpath):
            buf += "<td class='img'><a href='%s'><img src='%s' style='max-height:100px'></td></a>" % (imgpath, imgpath)
        else:
            buf += "<td class='img'></td>"

        buf += "</tr>\n"

    buf += "</table>\n"
    buf += "</body>\n"

    with open(report_filename, "w") as f:
        f.write(buf)

    print "Report file: " + report_filename
    print ""

def compare_and_sort_by_ted(src_function, src_program, dst_program):
    src_function_short = get_short_function_name(src_function)
    src_vector_file = src_program
    dst_vector_file = dst_program + ".dmp"

    data = read_pickle(src_vector_file)[src_function_short]
    if not data: return False
    else:
        src_function_name   = data["FUNCTION_NAME"]
        src_cfg_vector      = data["CFT"]
        src_abr             = data["ABR"]
        src_mnems           = data["MNEMS"]

    src_cfg_vector = ged.AnnotatedTree(src_cfg_vector)
    dst_dumped_data_list = read_pickle(dst_vector_file)

    results = []
    for (dst_function_name, data) in dst_dumped_data_list.items():
        dst_cfg_vector = data["CFT"]
        dst_abr        = data["ABR"]
        dst_mnems      = data["MNEMS"]
        dst_cfg_vector = ged.AnnotatedTree(dst_cfg_vector)

        distance1 = cfg_distance4(src_cfg_vector, dst_cfg_vector)
        distance2 = cfg_distance5(src_mnems, dst_mnems)

        result = {}
        result["DISTANCE1"]     = distance1
        result["DISTANCE2"]     = distance2
        result["FUNCTION_NAME"] = dst_function_name
        result["ABR"]           = dst_abr
        results.append(result)

    results = sorted(results, key=(lambda x: (x["DISTANCE1"], x["DISTANCE2"])))
    stats = {}
    stats["src_abr"]            = src_abr
    stats["dst_function_num"]   = len(dst_dumped_data_list)

    return (results, stats)

def search_function(src_function, src_program, dst_program, f_top):
    threshold = 40
    #threshold = -1 # ALL

    compare_results = compare_and_sort_by_ted(src_function, src_program, dst_program)
    if not compare_results:
        return False
    else:
        (results, stats) = compare_results

    (rank, dist) = (0, -1)
    for (i, result) in enumerate(results):
        (tmp_rank, tmp_dist) = (i + 1, result["DISTANCE1"])
        if tmp_dist > dist:
            (rank, dist) = (tmp_rank, tmp_dist)
        result["RANK"] = rank

    (next_rank, tmp_rank) = (len(results) + 1, results[-1]["RANK"])
    for result in results[::-1]:
        if result["RANK"] < tmp_rank:
            (next_rank, tmp_rank) = (tmp_rank, result["RANK"])
        result["NEXT_RANK"] = next_rank

    if f_top: threshold = results[0]["NEXT_RANK"] - 1

    return (results[:threshold], stats)


def main(src_program, src_function, dst_program, f_silent, f_image, f_overwrite, f_top):
    sys.setrecursionlimit(3000)
    start_time = time.time()

    search_results = search_function(src_function, src_program, dst_program, f_top)
    if not search_results: return False
    else:
        (results, stats) = search_results

    result_time = time.time() - start_time
    stats["time"] = result_time

    if not f_silent:
        print_results(results, stats, src_program, src_function, dst_program)

        """
        if f_image:
            def image_dump(program, function, f_overwrite):
                function_short = get_short_function_name(function)

                if not f_overwrite:
                    if os.path.exists(os.path.join(get_dump_png_path(program), function_short + ".png")):
                        return

                flag = ["-o"] if f_overwrite else []
                cmd = ["python", "idascript.py", program, "bingrep_dump2.py", "-f", function, "-i"] + flag
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.communicate()

            print "Top 10 function images were dumped."
        """

    return (results, stats)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description="")
    parser.add_argument('-sp', dest='src_program',  default="", type=str, help='')
    parser.add_argument('-sf', dest='src_function', default="", type=str, help='')
    parser.add_argument('-dp', dest='dst_program',  default="", type=str, help='')
    parser.add_argument('-i',  dest='f_image',      action='store_true', default=False, help='Output image as PNG)')
    parser.add_argument('-s',  dest='f_silent',     action='store_true', default=False, help="Don't print tesult to console")
    parser.add_argument('-o',  dest='f_overwrite',  action='store_true', default=False, help='Overwrite file')
    parser.add_argument('-t',  dest='f_top',        action='store_true', default=False, help='')
    args = parser.parse_args()

    src_program     = args.src_program
    src_function    = args.src_function
    dst_program     = args.dst_program

    f_silent        = args.f_silent
    f_image         = args.f_image
    f_overwrite     = args.f_overwrite
    f_top           = args.f_top

    src_program = AskFile(0, "*.dmp", "Select Src .dmp File")
    src_function = AskStr("sub_", "Input Function Name")
    dst_program = idaapi.get_root_filename()

    main(src_program, src_function, dst_program, f_silent, f_image, f_overwrite, f_top)




