# BinGrep, version 1.0.0
# Copyright 2017 Hiroki Hada
# distutils: language=c++
# coding:UTF-8

from libc.stdlib cimport malloc
from libc.string cimport memset
from libcpp.vector cimport vector
from libcpp.map cimport map

cdef int** zeros2(dim):
    assert len(dim) == 2
    cdef int i
    cdef int **matrix

    matrix = <int**> malloc(sizeof(int*) * dim[0])

    for i in range(dim[0]):
        matrix[i] = <int*> malloc(sizeof(int) * dim[1])
        memset(matrix[i], 0, sizeof(int) * dim[1])

    return matrix

cdef int* list_str2carray(list_str):
    cdef int i
    cdef int *array
    cdef int tmp

    length = len(list_str)
    array = <int*> malloc(sizeof(int) * length)

    for i, s in enumerate(list_str):
        tmp = 0
        for c in s:
            tmp += ord(c)
            tmp &= 0xFF

        array[i] = tmp

    return array

cpdef get_lcs_len(list_a, list_b):
    cdef int **table
    cdef int *arr_a, *arr_b
    cdef int i, j

    table = zeros2((len(list_a)+1, len(list_b)+1))
    arr_a = list_str2carray(list_a)
    arr_b = list_str2carray(list_b)

    for i in range(len(list_a)):
        for j in range(len(list_b)):
            if arr_a[i] == arr_b[j]:
                table[i+1][j+1] = table[i][j] + 1
            else:
                table[i+1][j+1] = max(table[i+1][j], table[i][j+1])

    return table[len(list_a)][len(list_b)]





