# BinGrep, version 1.0.0
# Copyright 2017 Hiroki Hada
# coding:UTF-8

class Node(object):
    def __init__(self, label):
        (self.label, self.children) = (label, list())

    @staticmethod
    def get_children(node): return node.children

    @staticmethod
    def get_label(node): return node.label

    def addkid(self, node):
        self.children.append(node)
        return self



