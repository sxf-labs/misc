#!/usr/bin/env python

import sys
import yaml
import logging as log
from pyparsing import *
from dict2xml import dict2xml
from xml.dom.minidom import parse, parseString, Text, Element

#log.basicConfig(format='%(levelname) 5s # %(asctime)s # %(message)s', level=log.DEBUG)
log.basicConfig(format='%(levelname) 5s # %(asctime)s # %(message)s', level=log.INFO)

class SEBNF:

  def __init__(self,gfilename,sfilename,ofilename):
    self.t = Text()
    self.builtin_grammar()
    self.parseFilename(gfilename)
    self.render("debug.xml")
    self.grammar()
    self.parseSource(sfilename,ofilename)
     
  def parseSource(self,sfilename,ofilename):
    f=open(sfilename,"r")
    buffer=str(f.read())
    f.close()
    try:
      self.displayRepository()
      self.data=self.repo[self.root].parseString(buffer)
    except ParseException,err:
      f.close()
      print "err",err
      return
    self.data=dict2xml({"root":self.data[0]}).doc
    self.render("odebug.xml")
    self.reduce()
    self.render(ofilename)

  def parseFilename(self,ifilename):
    f=open(ifilename,"r")
    buffer=str(f.read())
    f.close()
    try:
      self.data=self.syntax.parseString(buffer)
    except ParseException,err:
      f.close()
      print "err",err
      return
    self.data=dict2xml(self.data[0]).doc
    self.reduce()
    self.render("debug.xml")
    
  def displayRepository(self):
    print "rules's repository"
    for k,v in self.repo.iteritems():
      print "\t",k,":\t",v
    print "rules's keep"
    for k in self.keepTagNames:
      print "\t",k

  def hasAnnotation(self,el,annotation):
    return annotation in self.extractValue(el,"annotationidentifier")

  def extractOneValue(self,el,tagname):
    ret=self.extractValue(el,tagname)
    if len(ret)==0:
      log.error("no tagname %s in %s"%(tagname,el))
      return None
    if len(ret)>1:
      log.warn("multiple tagname %s in %s"%(tagname,el))
      return ret[0]
    return ret[0]           

  def extractValue(self,el,tagname):
    ret=el.getElementsByTagName(tagname)
    if not ret or len(ret)==0 : return []
    rets=[]
    for r in ret:
      rets.append(self.text(r.childNodes))
    return rets

  def getChild(self,el,tagname):
    for child in el.childNodes:
      if child.tagName in tagname:
        return child
    return None

  def flat(self,l):
    return [item for sublist in l for item in sublist]
        
  def extractTokenDefinition(self,el):
   if el.tagName in ["singledefinitionor","singledefinitionand","syntatictermkeep","syntatictermsuppress","groupedsequence"]:
     ret=[]
     for ch in el.childNodes:
      r=self.extractTokenDefinition(ch)
      if type(r)==list:
        ret.extend(r)
      else:
        ret.append(r)
     return ret
   if el.tagName == "builtin":
     b=self.text(el.childNodes)
     if not b in self.repo:
       log.error("the builtin %s is not in repo"%b)
     return self.repo[self.text(el.childNodes)]
   if el.tagName == "terminal":
     b=self.text(el.childNodes)
     return b
   log.error("the body's rule is not matched : %s %s"%(el,el.childNodes))    
   return None

  def extractRuleDefinition(self,el):
    if el==None: return None
    if el.tagName == "singledefinitionand":
      ret=None
      for ch in el.childNodes:
        if ret:
          ret=ret+self.extractRuleDefinition(ch)
        else:
          ret=self.extractRuleDefinition(ch)
      return ret
    if el.tagName == "singledefinitionor":
      ret=None
      for ch in el.childNodes:
        if ret:
          ret=ret|self.extractRuleDefinition(ch)
        else:
          ret=self.extractRuleDefinition(ch)
      return ret
    if el.tagName == "syntactictermkeep"      : return self.extractRuleDefinition(el.childNodes[0])
    if el.tagName == "syntactictermsuppress"  : return Suppress(self.extractRuleDefinition(el.childNodes[0]))
    if el.tagName == "groupedsequence"        : return self.extractRuleDefinition(el.childNodes[0])
    if el.tagName == "repeatedsequence"       : return ZeroOrMore(self.extractRuleDefinition(el.childNodes[0]))
    if el.tagName == "optionalsequence"       : return Optional(self.extractRuleDefinition(el.childNodes[0]))
    if el.tagName == "metaidentifier":
      b=self.text(el.childNodes)
      if not b in self.repo:
        self.forwards.append(b)
        self.repo[b]=Forward()
      return self.repo[b]
    if el.tagName == "builtin":
      b=self.text(el.childNodes)
      if not b in self.repo:
        log.error("the builtin %s is not in repo"%b)
      return self.repo[self.text(el.childNodes)]
    if el.tagName == "terminal":
      b=self.text(el.childNodes)
      return Literal(b)
    log.error("the body's rule is not matched : %s %s"%(el,el.childNodes))    
    return None
                      
  def grammar_builtin(self):
    self.repo["@nums"]=nums
    self.repo["@alphas"]=alphas
    self.repo["@string"]=quotedString
    self.repo["@alphanums"]=alphanums
    self.repo["@newline"]=LineEnd()
    self.repo["@comments"]=cStyleComment
    self.repo_keys.extend(self.repo.keys())

  def grammar_literal(self,rule):
    if not self.hasAnnotation(rule,"@literal"): return 
    metaIdentifier=self.extractOneValue(rule,"metaidentifier")
    if self.hasAnnotation(rule,"@keep"): self.keepTagNames.append(metaIdentifier)
    terminal=self.extractOneValue(rule,"terminal")
    log.debug("grammar_literal: %s->%s"%(metaIdentifier,terminal))
    self.repo_keys.append(metaIdentifier)
    self.repo[metaIdentifier]=Literal(terminal)

  def grammar_token(self,rule):
    if not self.hasAnnotation(rule,"@token"): return 
    metaIdentifier=self.extractOneValue(rule,"metaidentifier")
    if self.hasAnnotation(rule,"@keep"): self.keepTagNames.append(metaIdentifier)
    definition=self.extractTokenDefinition(self.getChild(rule,["singledefinitionor","singledefinitionand","groupedsequence"]))
    log.debug("grammar_token: %s->%s"%(metaIdentifier,definition))
    self.repo_keys.append(metaIdentifier)
    self.repo[metaIdentifier]=Word(*definition)

  def grammar_rule(self,rule):
    if not self.hasAnnotation(rule,"@rule"): return 
    metaIdentifier=self.extractOneValue(rule,"metaidentifier")
    if self.hasAnnotation(rule,"@keep"): self.keepTagNames.append(metaIdentifier)
    definition=self.extractRuleDefinition(self.getChild(rule,["singledefinitionor","singledefinitionand","groupedsequence"]))
    log.debug("grammar_rule: %s->%s"%(metaIdentifier,definition))
    if metaIdentifier in self.forwards:
      self.repo[metaIdentifier]<<definition
    else:
      self.repo_keys.append(metaIdentifier)
      self.repo[metaIdentifier]=definition
    if self.hasAnnotation(rule,"@start"):
      self.root=metaIdentifier

  def grammar(self):
    """
      Cree la grammaire 
    """
    self.repo_keys=[]
    self.repo=dict()
    self.forwards=[]
    self.keepTagNames=[]
    self.grammar_builtin()
    for rule in self.data.getElementsByTagName("rule"):
      self.grammar_literal(rule)
      self.grammar_token(rule)
      self.grammar_rule(rule)
    for k in self.repo:
      if isinstance(self.repo[k],ParserElement):
        self.repo[k].setParseAction(self.add_parse_idents("_parse_",k))
#    self.displayRepository()
#    sys.exit(0)
    
  def text(self,nodelist):
    """
      Contenu text du noeud.
    """
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)
    
  def render(self,ofilename,data=None):    
    """
      Ecrit les donnees du fichier xml
    """
    if not data: data=self.data
    f=open(ofilename,"w")
    f.write(data.toprettyxml())
    f.close()
            
  def reduce(self):
    """
      Reduit l'arbre:
        - simplifie les noeuds avec un seul fils.
        - supprime les noeuds avec aucun fils.
    """
    self.loop=True
    while self.loop:
      self.loop=False
      self.reduceEmpty(self.data)
      self.reduceSingle(self.data)
    
  def getTagsCount(self,nodelist):
    """
      Count combien de noeud fils de type ELEMENT_NODE contient ce noeud.
    """
    ret=0
    for node in nodelist:
        if node.nodeType == node.ELEMENT_NODE:
          ret+=1
    return ret

  def reduceEmpty(self,data):
    """
      Si le noeud XML contient aucun fils. Il est supprime,
      sauf si ce noeud fait parti de la liste de ceux que l'on garde (self.keepTagNames).    
    """
    if len(data.childNodes)==0 and data.parentNode!=None and data.nodeType!=data.TEXT_NODE and not data.tagName in self.keepTagNames:
      self.loop=True
      log.debug("reduce empty tag %s",data)
      data.parentNode.removeChild(data)
      data.unlink()
    else:
      for child in data.childNodes:
        self.reduceEmpty(child)
 
  def reduceSingle(self,data):
    """
      Si le noeud XML ne contient qu'un seul fils. Il est remplace par son fils,
      sauf si ce noeud fait parti de la liste de ceux que l'on garde (self.keepTagNames).    
    """
    if self.getTagsCount(data.childNodes)==1 and data.nodeType!=data.TEXT_NODE:
      log.debug("reduce single tag %s",data)
      if data.parentNode and not data.tagName in self.keepTagNames: 
        self.loop=True
        tmp=data.parentNode
        data.parentNode.replaceChild(data.childNodes[0],data)
        data=tmp
    for child in data.childNodes:
      self.reduceSingle(child)

  def parse(self,key,str,loc,toks):
    """
      Methodes generiques qui construits un dictionaire avec les tokens
      obtenus et la cle passe en parametres
    """
    log.debug("%s -> %s"%(key,toks))
    d=dict()
    d[key]=[]
    for tok in toks:
      d[key].append(tok)
    return d

  def add_builtin_parse_function(self):
    """
      Ajout des methodes parse_XXX ou XXX est une action pour chaque regles de 
      la grammaire EBNF. 
      Ces methodes sont ajouter dynamiquement pendant l'execution.
      Les methodes actions construisent un repo (self.repo) qui est un
      dictionnaire avec en cle l'identifiant et valeur la definition de la regle
      avec des objets pyparsing. 
    """
    idents=[]
    idents.append("metaidentifier")
    idents.append("token")
    idents.append("terminal")
    idents.append("builtin")
    idents.append("annotationidentifier")
    idents.append("definitionslist")
    idents.append("optionalsequence")
    idents.append("repeatedsequence")
    idents.append("groupedsequence")
    idents.append("syntacticprimary")
    idents.append("syntacticprimaries")
    idents.append("syntactictermkeep")
    idents.append("syntactictermsuppress")
    idents.append("singledefinitionand")
    idents.append("singledefinitionor")
    idents.append("annotationargs")
    idents.append("annotation")
    idents.append("annotations")
    idents.append("rule")
    idents.append("comment")
    idents.append("program")
    for ident in idents:
      self.add_parse_idents("parse_",ident)
    
  def add_parse_idents(self,root,ident):
    def parseInner(self, str, loc, toks):
      log.debug("parse %s : toks->%s"%(ident,toks))
      return self.parse("%s"%ident, str, loc, toks)
    parseInner.__name__="%s%s"%(root,ident)
    setattr(self.__class__,parseInner.__name__,parseInner) 
    return getattr(self,parseInner.__name__)

  def builtin_grammar(self):
    """
      Definition de la grammaire EBNF en utilisant bibliotheques pyparsing.
    """
    # Initialisation des methodes parseAction pour la grammaires EBNF
    self.add_builtin_parse_function()

    self.keepTagNames=[]
    self.keepTagNames.append("optionalsequence")
    self.keepTagNames.append("repeatedsequence")
    self.keepTagNames.append("groupedsequence")
    self.keepTagNames.append("syntatictermkeep")
    self.keepTagNames.append("syntactictermsuppress") 
        
    meta_identfier = Word(alphas, alphanums + '_').setParseAction(self.parse_metaidentifier)
    token          = Word(printables).setParseAction(self.parse_token)
    terminal       = ( Suppress("'") + CharsNotIn("'") + Suppress("'") ^ Suppress('"') + CharsNotIn('"') + Suppress('"') ).setParseAction(self.parse_terminal)                  
    
    knums         = Literal("@nums")
    kalphas       = Literal("@alphas")
    kstring       = Literal("@string")
    kalphanums    = Literal("@alphanums")
    kendline      = Literal("@newline")
    kwhitespaces  = Literal("@comments")
 
    builtin    = ( knums | kalphas | kalphanums | kwhitespaces | kendline | kstring ).setParseAction(self.parse_builtin)
 
    meta_identifier = Word(alphas, alphanums + '_').setParseAction(self.parse_metaidentifier)
    
    annotation_identifier = Word('@',alphanums + '_').setParseAction(self.parse_annotationidentifier)

    definitions_list = Forward().setParseAction(self.parse_definitionslist)

    optional_sequence = ( Suppress('[') + definitions_list + Suppress(']') ).setParseAction(self.parse_optionalsequence)

    repeated_sequence = ( Suppress('{') + definitions_list + Suppress('}') ).setParseAction(self.parse_repeatedsequence)

    grouped_sequence  = ( Suppress('(') + definitions_list + Suppress(')') ).setParseAction(self.parse_groupedsequence)

    syntactic_primary = ( builtin | optional_sequence | repeated_sequence | grouped_sequence | meta_identifier | terminal ).setParseAction(self.parse_syntacticprimary)

    syntactic_primaries = OneOrMore( syntactic_primary ).setParseAction(self.parse_syntacticprimaries)
    
    syntactic_term_keep     = ( syntactic_primaries ).setParseAction(self.parse_syntactictermkeep)

    syntactic_term_suppress = ( Suppress('~') + syntactic_primaries ).setParseAction(self.parse_syntactictermsuppress)

    single_definition = ( delimitedList(syntactic_term_keep | syntactic_term_suppress, ',') ).setParseAction(self.parse_singledefinitionand)

    definitions_list << ( delimitedList(single_definition, '|') ).setParseAction(self.parse_singledefinitionor)

    annotation_args = ( meta_identifier + Suppress('=') + CharsNotIn(",)") ).setParseAction(self.parse_annotationargs)

    annotation = ( annotation_identifier + Optional( Suppress('(') + delimitedList(annotation_args,',') + Suppress(')') ) ).setParseAction(self.parse_annotation)

    annotations = ( ZeroOrMore( annotation ) ).setParseAction(self.parse_annotations)

    syntax_rule = ( annotations + meta_identifier + Suppress('=') + definitions_list.setParseAction(self.parse_groupedsequence) + Suppress(';') ).setParseAction(self.parse_rule)

    ebnfComment = ( ( "(*" + ZeroOrMore( CharsNotIn("*") | ( "*" + ~Literal(")") ) ) + "*)" ) ).setParseAction(self.parse_comment)

    self.syntax = ( OneOrMore(syntax_rule | ebnfComment ) ).setParseAction(self.parse_program)

if __name__ == '__main__':
  if len(sys.argv)!=4:
    print "Usage: %s <grammar> <source> <output:xml>"%sys.argv[0]
    sys.exit(0)
  SEBNF(sys.argv[1],sys.argv[2],sys.argv[3])

