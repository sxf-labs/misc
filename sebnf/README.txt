
Ce programme de demonstration est un brouillon qui à partir d'une grammaire de
style EBNF permet de transformer une source en un fichier XML.

Pour exécuter un test du programme python sebnf.py, il faut exécuter :

	./run.sh

l'usage de sebnf.py est :

	Usage: ./sebnf.py <grammar> <source> <output:xml>

où :

	grammar : est une grammaire au format SEBNF
	source : le fichier source à parser 
	output:xml : est le fichier résultat du parsing au format XML

Voici un extrait de parsing d'expression arithmétique:

source SEBNF:

	@literal
	mul = "*" ;
	
	@literal
	div = "/" ;
	
	@literal
	add = "+" ;
	
	@literal
	sub = "-" ;
	
	@token
	@keep
	var = @alphas, @alphanums ;
	
	@token
	@keep
	number = @nums ;
	
	@rule
	mulop = mul | div ; 
	
	@rule
	addop = add | sub ;
	
	@rule
	factor = ( ~"(", expression, ~")" ) | var | number ;
	
	@rule
	term = factor, { mulop, factor } ;
	
	@rule
	expression = term, { addop, term } ;
	
	@rule
	assignment = var, ~"=", expression ;
	
	@rule
	assignments = { assignment } ;
	
	@rule
	@start
	program = assignments ;
	
le fichier source qu'il parse
	
	a=2+b*c
	cd=bc*de
	
et le résultat XML 
	
	<?xml version="1.0" ?>
	<program>
		<assignment>
			<var>a</var>
			<expression>
				<number>2</number>
				<add>+</add>
				<term>
					<var>b</var>
					<mul>*</mul>
					<var>c</var>
				</term>
			</expression>
		</assignment>
		<assignment>
			<var>cd</var>
			<term>
				<var>bc</var>
				<mul>*</mul>
				<var>de</var>
			</term>
		</assignment>
	</program>
	

