#!/usr/bin/python

class Primitive (object):
	"""docstring for primitive """
	def __init__(self, name, domain, parameters, preconditions, effects):
		self.__name__ = name.upper()
		self.domain = domain
		self.setParameters(parameters)
		self.preconditions = preconditions
		self.effects = effects[1:]


	def  __call__(self, State, *args):
		if(self.checkArgs(State, args) == True):
			if(self.checkPreconditions(State) == True):
				State1 = self.execPrimitiveEffects(State, args)
				return State1
		return False

	def setParameters(self, parameters):
		self.params = []
		for i in range(len(parameters)):
			if parameters[i] == "-":
				if parameters[i+1].upper() in self.domain.types:
					self.params.append([parameters[i-1], parameters[i+1].upper()])
				else:
					raise Exception ("Type " + parameters[i+1].upper() + " not defined")


	def checkArgs(self, state, *args):
		self.linkedParams = {}
		for arg in args:
			for i in range(len(arg)):
				if self.domain.objList[arg[i]].upper() != self.params[i][1]:
					return False
				else:
					self.linkedParams.update({self.params[i][0]:arg[i]})
		return True



	def checkPreconditions(self, State):
		if self.preconditions[0] == "and":
			return self.checkPreconditionsAnd(State, self.preconditions[1:])
		elif self.preconditions[0] == "or":
			return self.checkPreconditionsOr(State, self.preconditions[1:])
		prec = getattr(State, self.preconditions[0][0].upper(), False)
		if prec == False:
			raise Exception("Token " + str(self.preconditions[0][0]).upper() + " not defined")
		else:
			aux = []
			for i in range(1, len(self.preconditions[0])):
				#Filling the auxiliar list...
				aux.append(self.linkedParams[self.preconditions[0][i]])
			print aux
			match = False
			#Check with the state
			for j in range(len(prec)):
				if aux == prec[j]:
					match = True

			return match




	def checkPreconditionsAnd(self, State, preconditionAuxList):
		#For all preconditions
		for i in range(len(preconditionAuxList)):
			#Take 1
			precondition = preconditionAuxList[i]
			#If theres a list with an OR statement
			if precondition[0] == "or":
				#Check the OR sublist
				if checkPreconditionsOr(State, precondition[1:]) == False:
					return False
 			else:
 				#Check with the state
 				predicate = getattr(State, precondition[0].upper(), False)
 				#Lexic control
 				if predicate == False:
 					raise Exception(precondition[0].upper() + " not defined")
 				else:
 					#Auxiliar list with the parameters
 					aux = []
 					for j in range(1, len(precondition)):
 						#Filling the auxiliar list...
 						aux.append(self.linkedParams[precondition[j]])
 					match = False
 					#Check with the state
 					for j in range(len(predicate)):
 						if aux == predicate[j]:
 							match = True
 					#if theres no match finish(its an AND we only need 1 missmatch to return False)
 					if match == False:
 						return False

 		return True


	def checkPreconditionsOr(self, State, preconditionAuxList):
		if self.domain.adl == True:
			#For all preconditions
			for i in range(len(preconditionAuxList)):
				#Take 1
				precondition = preconditionAuxList[i]
				#If theres a list with an OR statement
				if precondition[0] == "and":
					#Check the OR sublist
					if checkPreconditionsAnd(State, precondition[1:]) == True:
						return True
	 			else:
	 				#Check with the state
	 				predicate = getattr(State, precondition[0].upper(), False)
	 				#Lexic control
	 				if predicate == False:
	 					raise Exception(precondition[0].upper() + " not defined")
	 				else:
	 					#Auxiliar list with the parameters
	 					aux = []
	 					for j in range(1, len(precondition)):
	 						#Filling the auxiliar list...
	 						aux.append(self.linkedParams[precondition[j]])
	 					match = False
	 					#Check with the state
	 					for j in range(len(predicate)):
	 						if aux == predicate[j]:
	 							match = True
	 					#if theres no match finish(its an OR we only need 1 match to return True)
	 					if match == True:
	 						return True

	 		return False
	 	else:
	 		raise Exception("Or statements disabled without :adl tag")


	def execPrimitiveEffects(self, State, *args):
		effect = []
		newState = State
		for i in range(len(self.effects)):
			effect = self.effects[i]

			if effect[0] == "not":
				effect = effect[1]
				aux = []
	 			for j in range(1, len(effect)):
	 				aux.append(self.linkedParams[effect[j]])

	 			auxEffect = getattr(newState, effect[0].upper(), False)
				if auxEffect != False:
					if auxEffect != "__NON_DEFINED__":
						auxEffect.append(aux)
						setattr(newState, effect[0].upper(), auxEffect)
					else:
						auxEffect = aux
						setattr(newState, effect[0].upper(), auxEffect)
				else:
					raise Exception(effect[0].upper() + " predicate not defined")

			else:
				aux = []
	 			for j in range(1, len(effect)):
	 				aux.append(self.linkedParams[effect[j]])

	 			auxEffect = getattr(newState, effect[0].upper(), False)
				if auxEffect != False:
					if auxEffect != "__NON_DEFINED__":
						auxEffect.append(aux)
						setattr(newState, effect[0].upper(), auxEffect)
					else:
						auxEffect = aux
						setattr(newState, effect[0].upper(), auxEffect)
				else:
					raise Exception(effect[0].upper() + " predicate not defined")

		return newState
		
		