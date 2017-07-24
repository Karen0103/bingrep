# BinGrep, version 1.0.0
# Copyright 2017 Hiroki Hada
# distutils: language=c++
# coding:UTF-8

import collections

from libc.stdlib cimport malloc
from libc.string cimport memset
from libc.stdlib cimport qsort

from libcpp.vector cimport vector
from libcpp.map cimport map


cdef int* zeros1(n):
    cdef int i
    cdef int *array

    array = <int*> malloc(sizeof(int) * n)
    memset(array, 0, sizeof(int) * n)

    return array

cdef int** zeros2(dim):
    assert len(dim) == 2
    cdef int i
    cdef int **matrix

    matrix = <int**> malloc(sizeof(int*) * dim[0])

    for i in range(dim[0]):
        matrix[i] = <int*> malloc(sizeof(int) * dim[1])
        memset(matrix[i], 0, sizeof(int) * dim[1])

    return matrix

cdef int* clist_int2carray(clist_int):
    cdef int i
    cdef int *array

    length = clist_int.len()
    array = <int*> malloc(sizeof(int) * length)

    for i, x in enumerate(clist_int):
        array[i] = <int> x

    return array

cdef int strdist(unsigned int a, unsigned int b):
    if a == b:
        return <int> 0
    else:
        return <int> 1


ctypedef struct _clist_int_struct:
    int data
    _clist_int_struct *next

cdef class clist_int:
    cdef _clist_int_struct *_head
    cdef _clist_int_struct *_tail
    cdef int _len

    def __cinit__(self):
        (self._head, self._tail, self._len) = (<_clist_int_struct*>NULL, <_clist_int_struct*>NULL, 0)

    cpdef void append(self, int data):
        cdef _clist_int_struct *obj = <_clist_int_struct*> malloc(sizeof(_clist_int_struct))

        (obj.data, obj.next) = (data, <_clist_int_struct*>NULL)
        self._len += 1

        if self._head is NULL:
            (self._head, self._tail) = (obj, obj)
        else:
            (self._tail.next, self._tail) = (obj, obj)

    cpdef int len(self):
        return self._len

    def __iter__(self):
        cdef _clist_int_struct *ptr = self._head
        while ptr is not NULL:
            yield ptr.data
            ptr = ptr.next


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

class AnnotatedTree(object):
    def __init__(self, root):
        cdef int i, j, nid, lmd

        self.root       = root
        self.keyroots   = None
        self.nodes      = list()
        self.lmds       = clist_int()
        self.ids        = clist_int()

        stack           = list()
        pstack          = list()
        stack.append((root, collections.deque()))
        j = 0

        while len(stack) > 0:
            n, anc = stack.pop()
            nid = j

            for c in Node.get_children(n):
                a = collections.deque(anc)
                a.appendleft(nid)
                stack.append((c, a))

            pstack.append(((n, nid), anc))
            j += 1

        cdef map[int, int] lmds
        cdef map[int, int] keyroots

        i = 0

        while len(pstack) > 0:
            (n, nid), anc = pstack.pop()

            self.nodes.append(n)
            self.ids.append(nid)

            if not Node.get_children(n):
                lmd = i
                for a in anc:
                    if lmds.find(a) == lmds.end():
                        lmds[a] = i
                    else: break
            else:
                lmd = lmds[nid]

            self.lmds.append(lmd)
            keyroots[lmd] = i
            i += 1

        self.keyroots = sorted(keyroots.values())

cdef int insert_cost(node):
    return strdist(<unsigned int> 1, node)

cdef int remove_cost(node):
    return strdist(node, <unsigned int> 1)

cdef int update_cost(a, b):
    return strdist(a, b)

cdef int min3(int a, int b, int c):
    cdef int t
    t = a if a < b else b
    t = t if t < c else c
    return t

cpdef int simple_distance(A, B):
    cdef int **treedists
    cdef int **fd
    cdef int *Al
    cdef int *Bl
    cdef int i, j

    cdef int lenA
    cdef int lenB
    lenA = <int>len(A.nodes)
    lenB = <int>len(B.nodes)

    treedists = zeros2((lenA, lenB))

    Al = clist_int2carray(A.lmds)
    Bl = clist_int2carray(B.lmds)

    cdef unsigned int *An
    cdef unsigned int *Bn
    An = <unsigned int*> malloc(sizeof(unsigned int) * lenA)
    Bn = <unsigned int*> malloc(sizeof(unsigned int) * lenB)

    for i in range(lenA):
        An[i] = Node.get_label(A.nodes[i])

    for i in range(lenB):
        Bn[i] = Node.get_label(B.nodes[i])

    cdef int m, n
    cdef int p, q
    cdef int x, y
    cdef int ioff, joff

    for i in A.keyroots:
        for j in B.keyroots:
            (m, n)       = (i - Al[i] + 2, j - Bl[j] + 2)
            (ioff, joff) = (Al[i] - 1, Bl[j] - 1)
            fd = zeros2((m,n))

            for x in xrange(1, m): fd[x][0] = fd[x-1][0] + remove_cost(An[x+ioff])
            for y in xrange(1, n): fd[0][y] = fd[0][y-1] + insert_cost(Bn[y+joff])

            for x in xrange(1, m):
                for y in xrange(1, n):
                    if Al[i] == Al[x+ioff] and Bl[j] == Bl[y+joff]:
                        fd[x][y] = min3(
                            fd[x-1][y]   + remove_cost(An[x+ioff]),
                            fd[x][y-1]   + insert_cost(Bn[y+joff]),
                            fd[x-1][y-1] + update_cost(An[x+ioff], Bn[y+joff])
                        )
                        treedists[x+ioff][y+joff] = fd[x][y]

                    else:
                        p = Al[x+ioff] - 1 - ioff
                        q = Bl[y+joff] - 1 - joff
                        fd[x][y] = min3(
                            fd[x-1][y] + remove_cost(An[x+ioff]),
                            fd[x][y-1] + insert_cost(Bn[y+joff]),
                            fd[p][q]   + treedists[x+ioff][y+joff]
                        )

    return treedists[lenA-1][lenB-1]





