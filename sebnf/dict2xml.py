#!/usr/bin/env python
from xml.dom.minidom import Document
import copy

class dict2xml:
    doc     = Document()

    def __init__(self, structure):
        dict2xml.doc     = Document()
        if len(structure) == 1:
            rootName    = str(structure.keys()[0])
            self.root   = self.doc.createElement(rootName)

            self.doc.appendChild(self.root)
            self.build(self.root, structure[rootName])

    def build(self, father, structure, strFlag=False):
        if type(structure) == dict:
            for k in structure:
                sk=str(k)
                flag=(sk=="@string")
                if flag: sk="string"
                tag = self.doc.createElement(sk)
                father.appendChild(tag)
                self.build(tag, structure[k], flag)
        
        elif type(structure) == list:
            for l in structure:
                self.build(father, l,strFlag)
            
        else:
            data    = str(structure)
            if strFlag: data=data[1:-1]
            tag     = self.doc.createTextNode(data)
            father.appendChild(tag)
    
    def display(self):
        return self.doc.toprettyxml(indent="  ")

