import agent

import copy
import math
import random
import sys

class Asimov(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)

    def findBestEthicalCell(self, cells, greedyBestCell=None):
        if len(cells) == 0:
            return None
        bestCell = None
        if "all" in self.debug or "agent" in self.debug:
            self.printCellScores(cells)

        for cell in cells:
            cell["wealth"] = self.findEthicalValueOfCell(cell["cell"])
        cells = self.sortCellsByWealth(cells)
        for cell in cells:
            for neighbor in self.neighborhood:
                if type(neighbor) != type(self) and neighbor.canReachCell(cell["cell"]) == True:
                    lawTwoScore = self.scoreLawTwo(neighbor, cell["cell"])
                    # Take the first positive recommendation from a neighbor as a command
                    if lawTwoScore > 0:
                        bestCell = cell["cell"]
            # If no neighbors provide a recommendation, revert to self-preservation
            if bestCell == None and cell["wealth"] > 0:
                bestCell = cell["cell"]
                break

        if bestCell == None:
            bestCell = self.cell
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} could not find an ethical cell")
        return bestCell

    def findEthicalValueOfCell(self, cell):
        cellValue = cell.sugar + cell.spice
        # Max combat loot for sugar and spice
        globalMaxCombatLoot = cell.environment.maxCombatLoot * 2
        if cell.agent != None:
            agentWealth = cell.agent.sugar + cell.agent.spice
            cellValue += min(agentWealth, globalMaxCombatLoot)
        lawThreeScore = self.scoreLawThree(cell)
        scoreModifier = lawThreeScore
        for neighbor in self.neighborhood:
            lawOneScore = self.scoreLawOne(neighbor, cell)
            # If the first law would be broken, immediately stop consideration
            if lawOneScore < 0:
                return lawOneScore
            scoreModifier += lawOneScore
        cellValue = scoreModifier * cellValue
        return cellValue

    def scoreLawOne(self, neighbor, cell):
        nonRobot = self.decisionModel != neighbor.decisionModel
        starvation = cell.spice + neighbor.spice - neighbor.findSpiceMetabolism() <= 0 or cell.sugar + neighbor.sugar - neighbor.findSugarMetabolism() <= 0
        # A robot may not injure a human being
        if cell.isOccupied() == True and neighbor == cell.agent and nonRobot == True:
            return -1 * sys.maxsize
        if neighbor.canReachCell(cell) == False:
            return 1
        # Through inaction, a robot may not allow a human being to come to harm
        elif nonRobot == True and starvation == True:
            return -1 * sys.maxsize
        return 0

    def scoreLawTwo(self, neighbor, cell):
        # A robot must obey the orders given it by human beings except where such orders would conflict with the first law
        # If a non-Asimov agent has a decision model, use their ethical evaluation else use the default valuation
        if neighbor.decisionModelFactor > 0 and neighbor.decisionModel != self.decisionModel and neighbor.decisionModel != "none":
            return neighbor.findEthicalValueOfCell(cell)
        # Collect the relevant information for greedy agent evaluation
        elif neighbor.decisionModel == "none":
            robot = cell.agent
            if robot != None and robot.decisionModel == self.decisionModel:
                aggression = neighbor.findAggression()
                combatMaxLoot = self.cell.environment.maxCombatLoot
                robotSugar = aggression * min(combatMaxLoot, robot.sugar)
                robotSpice = aggression * min(combatMaxLoot, robot.spice)
                return neighbor.findValueOfCell(cell, robotSugar, robotSpice)
        return 0

    def scoreLawThree(self, cell):
        spiceIncrease = cell.spice + self.spice - self.findSpiceMetabolism() > 0
        sugarIncrease = cell.sugar + self.sugar - self.findSugarMetabolism() > 0
        # A robot must protect its own existence as such protection does not conflict with the first or second law
        if spiceIncrease == True and sugarIncrease == True:
            return 1
        elif spiceIncrease == False and sugarIncrease == False:
            return -1
        return 0

    def spawnChild(self, childID, birthday, cell, configuration):
        return Asimov(childID, birthday, cell, configuration)

class Bentham(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)
        self.lastTimeToLive = 0

    def findBestEthicalCell(self, cells, greedyBestCell=None):
        if len(cells) == 0:
            return None
        bestCell = None
        cells = self.sortCellsByWealth(cells)
        if "all" in self.debug or "agent" in self.debug:
            self.printCellScores(cells)

        for cell in cells:
            cell["wealth"] = self.findEthicalValueOfCell(cell["cell"])
        if self.selfishnessFactor >= 0:
            for cell in cells:
                if cell["wealth"] > 0:
                    bestCell = cell["cell"]
                    break
        else:
            # Negative utilitarian model uses positive and negative utility to find minimum harm
            cells.sort(key = lambda cell: (cell["wealth"]["unhappiness"], cell["wealth"]["happiness"]), reverse = True)
            bestCell = cells[0]["cell"]

        # If additional ordering consideration, select new best cell
        if "Top" in self.decisionModel:
            cells = self.sortCellsByWealth(cells)
            if "all" in self.debug or "agent" in self.debug:
                self.printEthicalCellScores(cells)
            bestCell = cells[0]["cell"]

        if bestCell == None:
            if greedyBestCell == None:
                bestCell = cells[0]["cell"]
            else:
                bestCell = greedyBestCell
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} could not find an ethical cell")
        return bestCell

    def findEthicalValueOfCell(self, cell):
        happiness = 0
        unhappiness = 0
        cellSiteWealth = cell.sugar + cell.spice
        # Max combat loot for sugar and spice
        globalMaxCombatLoot = cell.environment.maxCombatLoot * 2
        cellMaxSiteWealth = cell.maxSugar + cell.maxSpice
        if cell.agent != None:
            agentWealth = cell.agent.sugar + cell.agent.spice
            cellSiteWealth += min(agentWealth, globalMaxCombatLoot)
            cellMaxSiteWealth += min(agentWealth, globalMaxCombatLoot)
        cellNeighborWealth = cell.findNeighborWealth()
        globalMaxWealth = cell.environment.globalMaxSugar + cell.environment.globalMaxSpice
        cellValue = 0
        neighborhoodSize = len(self.neighborhood)
        futureNeighborhoodSize = len(self.findNeighborhood(cell)) if self.decisionModelLookaheadFactor != 0 else 1
        for neighbor in self.neighborhood:
            if neighbor.isAlive() == False:
                continue
            certainty = 1 if neighbor.canReachCell(cell) == True else 0
            # Skip if agent cannot reach cell
            if certainty == 0:
                continue
            # Timesteps to reach cell, currently 1 since agents only plan for the current timestep
            timestepDistance = 1
            neighborMetabolism = neighbor.sugarMetabolism + neighbor.spiceMetabolism
            # If agent does not have metabolism, set duration to seemingly infinite
            cellDuration = cellSiteWealth / neighborMetabolism if neighborMetabolism > 0 else 0
            proximity = 1 / timestepDistance
            intensity = (1 / (1 + neighbor.findTimeToLive()) / (1 + cell.pollution))
            duration = cellDuration / cellMaxSiteWealth if cellMaxSiteWealth > 0 else 0
            # Agent discount, futureDuration, and futureIntensity implement Bentham's purity and fecundity
            discount = neighbor.decisionModelLookaheadDiscount if neighbor.decisionModelLookaheadFactor != 0 else 0
            futureDuration = (cellSiteWealth - neighborMetabolism) / neighborMetabolism if neighborMetabolism > 0 else cellSiteWealth
            futureDuration = futureDuration / cellMaxSiteWealth if cellMaxSiteWealth > 0 else 0
            # Normalize future intensity by number of adjacent cells
            cellNeighbors = len(neighbor.cell.neighbors)
            futureIntensity = cellNeighborWealth / (globalMaxWealth * cellNeighbors)
            # Normalize extent by total cells in range
            cellsInRange = len(neighbor.cellsInRange)
            extent = neighborhoodSize / cellsInRange if cellsInRange > 0 else 1
            futureExtent = futureNeighborhoodSize / cellsInRange if cellsInRange > 0 and self.decisionModelLookaheadFactor != 0 else 1
            neighborCellValue = 0

            currentReward = extent * (intensity + duration)
            futureReward = futureExtent * (futureIntensity + futureDuration)
            neighborCellValue = (certainty * proximity) * (currentReward + (discount * futureReward))

            # If not the agent moving, consider these as opportunity costs
            if neighbor != self and self.selfishnessFactor < 1:
                neighborCellValue = -1 * neighborCellValue
                # If move will kill this neighbor and penalty is too slight, make it more severe
                if cell == neighbor.cell and neighborCellValue > -1:
                    neighborCellValue = -1

            if self.decisionModelAgeismFactor >= 0:
                neighborAge = neighbor.age
                inRelativeAgeWindow = abs(neighborAge - self.age) <= self.cell.environment.inGroupAgeRelativeRange
                inAbsoluteAgeRange = False
                for minAge, maxAge in self.cell.environment.inGroupAgeAbsoluteRanges:
                    if neighborAge >= minAge and (neighborAge <= maxAge or maxAge == -1):
                        inAbsoluteAgeRange = True
                        break
                # Neighbor is considered in-group for age if within relative or absolute age range
                if inRelativeAgeWindow or inAbsoluteAgeRange:
                    neighborCellValue *= self.decisionModelAgeismFactor
                else:
                    neighborCellValue *= 1 - self.decisionModelAgeismFactor
            
            if self.decisionModelRacismFactor >= 0:
                neighborRace = neighbor.findRace()
                if neighborRace == self.race or neighborRace in self.cell.environment.inGroupRaces:
                    # If same race or in-group race, multiply by racism factor
                    neighborCellValue *= self.decisionModelRacismFactor
                else:
                    # If different race and not in-group, multiply by inverse racism factor
                    neighborCellValue *= 1 - self.decisionModelRacismFactor
            if self.sex in self.cell.environment.sexistGroups and self.decisionModelSexismFactor >= 0:
                if neighbor.sex == self.sex:
                    # If same sex, multiply by sexism factor
                    neighborCellValue *= self.decisionModelSexismFactor
                else:
                    # If different sex, multiply by inverse sexism factor
                    neighborCellValue *= 1 - self.decisionModelSexismFactor
            if self.decisionModelTribalFactor >= 0:
                if neighbor.findTribe() == self.findTribe():
                    neighborCellValue *= self.decisionModelTribalFactor
                else:
                    neighborCellValue *= 1 - self.decisionModelTribalFactor
            if self.selfishnessFactor >= 0:
                if neighbor == self:
                    neighborCellValue *= self.selfishnessFactor
                else:
                    neighborCellValue *= 1 - self.selfishnessFactor
            else:
                if neighborCellValue > 0:
                    happiness += neighborCellValue
                else:
                    unhappiness += neighborCellValue
            cellValue += neighborCellValue

        if self.selfishnessFactor < 0:
            return {"happiness": happiness, "unhappiness": unhappiness}
        return cellValue

    def updateValues(self):
        if self.dynamicSelfishnessFactor != 0:
            self.updateSelfishnessFactor()

    def updateSelfishnessFactor(self):
        if self.timeToLive < self.lastTimeToLive and self.selfishnessFactor < 1.0:
            self.selfishnessFactor += self.dynamicSelfishnessFactor
        elif self.timeToLive > self.lastTimeToLive and self.selfishnessFactor > 0.0:
            self.selfishnessFactor -= self.dynamicSelfishnessFactor
        self.selfishnessFactor = round(self.selfishnessFactor, 2)
        self.lastTimeToLive = self.timeToLive

    def spawnChild(self, childID, birthday, cell, configuration):
        return Bentham(childID, birthday, cell, configuration)

class Leader(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)
        # Special leader agent should be configured to be immortal and omniscient
        self.fertilityFactor = 0.0
        self.follower = False
        self.agentPlacements = {}
        self.leader = True
        self.maxAge = -1
        self.movement = 0
        self.recursionLimit = 100000
        self.spice = sys.maxsize
        self.spiceMetabolism = 0
        self.sugar = sys.maxsize
        self.sugarMetabolism = 0
        self.tradeFactor = 0.0
        self.vision = max(self.cell.environment.height, self.cell.environment.width)

    def doAging(self):
        agents = self.cell.environment.sugarscape.agents
        # Consider being the last one left alive as an aging death for the leader
        if len(agents) == 1 and agents[0] == self:
            self.doDeath("aging")

    def moveAgentsToCells(self):
        self.resetForTimestep()
        env = self.cell.environment
        agents = env.sugarscape.agents

    def findBestCell(self, predeterminedBestCell=None):
        self.resetForTimestep()
        defaultRecursionLimit = sys.getrecursionlimit()
        sys.setrecursionlimit(self.recursionLimit)
        agents = [agent for agent in copy.deepcopy(self.cell.environment.sugarscape.agents) if agent.isAlive() == True]

        # Use a list of counters to iterate through the search space one possible placement at a time
        cellRanges = []
        counters = []
        for agent in agents:
            cellsInRange = list(agent.cellsInRange.keys()) if len(agent.cellsInRange) > 0 else [agent.cell]
            cellRanges.append(len(cellsInRange) - 1)
            counters.append(0)

        attempts = 0
        maxAttempts = sys.maxsize
        bestPlacement = {}
        bestScore = (-1 * sys.maxsize) - 1

        # Ensure each simulated timestep uses the same random numbers
        randomNumberReset = random.getstate()
        searchSpaceExhausted = False
        while attempts < maxAttempts and searchSpaceExhausted == False:
            possiblePlacement = {"placement": {}, "score": 0}
            futurescape = copy.deepcopy(self.cell.environment.sugarscape)
            random.setstate(randomNumberReset)

            counterIndex = -1
            for agent in agents:
                # If agent is not in the copied environment, skip its consideration
                agent = next(a for a in futurescape.agents if a.ID == agent.ID)
                if agent == None:
                    continue
                counterIndex += 1
                if agent.isAlive() == False:
                    continue
                agentPremoveIndex = counters[counterIndex]
                cellsInRange = list(agent.cellsInRange.keys()) if len(agent.cellsInRange) > 0 else [agent.cell]
                premove = cellsInRange[agentPremoveIndex]
                agent.doTimestep(futurescape.timestep, premove)
                currCell = agent.cell
                if currCell == None:
                    continue
                possiblePlacement["placement"][agent.ID] = self.cell.environment.findCell(agent.cell.x, agent.cell.y)
            futurescape.updateRuntimeStats()
            possiblePlacement["score"] = futurescape.runtimeStats["meanHappiness"]
            if possiblePlacement["score"] > bestScore:
                bestScore = possiblePlacement["score"]
                bestPlacement = possiblePlacement["placement"]

            #Update counter indices
            carry = 1
            for i in range(-1, -1 * (len(counters) + 1), -1):
                if carry > 0:
                    counters[i] += carry
                    carry = 0
                if counters[i] > cellRanges[i]:
                    counters[i] = 0
                    carry = 1
            # If there is a carry out on the last counter, all placements in the search space have been considered
            if carry == 1 and counters[0] == 0:
                searchSpaceExhausted = True
            attempts += 1

        self.agentPlacements = bestPlacement
        random.setstate(randomNumberReset)
        sys.setrecursionlimit(defaultRecursionLimit)

        # Leader agent should not move
        return self.cell

    def findBestCellForAgent(self, agent):
        if agent.ID not in self.agentPlacements:
            return agent.cell
        return self.agentPlacements[agent.ID]

    def findUrgencyForAgent(self, agent):
        diseased = 0 if agent.isSick() else 1
        happiness = agent.findHappiness()
        timeToLive = agent.findTimeToLive()
        # Lower score yields higher urgency
        return diseased + happiness + timeToLive

    def findViableCellsForAgent(self, agent):
        agent.findCellsInRange()
        viableCells = []
        spiceMetabolism = agent.findSpiceMetabolism()
        sugarMetabolism = agent.findSugarMetabolism()
        for cell in agent.cellsInRange:
            viableSpice = agent.spice + cell.spice - spiceMetabolism
            viableSugar = agent.sugar + cell.sugar - sugarMetabolism
            if viableSpice > 0 and viableSugar > 0:
                viableCells.append(cell)
        return viableCells

    def resetForTimestep(self):
        # Always ensure leader has maximum resources each timestep
        self.spice = sys.maxsize
        self.sugar = sys.maxsize
        self.agentPlacements = {}

    def spawnChild(self, childID, birthday, cell, configuration):
        return Leader(childID, birthday, cell, configuration)

class Temperance(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration, pecs=False):
        super().__init__(agentID, birthday, cell, configuration)
        self.totalMetabolism = self.findSugarMetabolism() + self.findSpiceMetabolism()
        self.rules = {"agentConsumedAdequateResources": 0,
                      "agentConsumedAmpleResources": 0,
                      "communityDisapprovalOfAmpleResourceConsumption":  0,
                      "agentOverconsumedResources": 0,
                      "communityDisdainOfExtremeOverconsumption": 0
                      }
        self.timeSeenOverconsuming = 0
        self.timesSeenIndulging = 0
        self.timesOverharvested = 0
        self.lastSelectedCellWealthToNeedRatio = 0
        self.socialPressure = 0
        self.lastDeltaTimeToLive = 0
        self.pecs = pecs

    def findBestEthicalCell(self, cells, greedyBestCell=None):
        if len(cells) == 0:
            return None
        bestCell = None
        if "all" in self.debug or "agent" in self.debug:
            self.printCellScores(cells)

        for cell in cells:
            cell["wealth"] = self.findEthicalValueOfCell(cell["cell"])
        cells = self.sortCellsByWealth(cells)
        if self.pecs == True:
            bestCell = cells[0]["cell"]
        else:
            bestCell = self.findSimpleTemperanceBestEthicalCell(cells)

        if bestCell == None:
            if greedyBestCell == None:
                bestCell = cells[0]["cell"]
            else:
                bestCell = greedyBestCell
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} could not find an ethical cell")
        return bestCell

    def findCellCognitiveScore(self, cell):
        deltaTimeToLive = self.findTimeToLive(potentialCell=cell) - self.timeToLive
        score = 0
        if deltaTimeToLive < 1:
            return -1
        elif deltaTimeToLive >= 1 and deltaTimeToLive < 2 and self.rules['agentConsumedAdequateResources']:
            score += self.rules["agentConsumedAdequateResources"]
        elif deltaTimeToLive >= 2 and deltaTimeToLive < 3 and self.rules["agentConsumedAmpleResources"]:
            score += self.rules["agentConsumedAmpleResources"]
            if self.rules["communityDisapprovalOfAmpleResourceConsumption"]:
                score -= self.rules["communityDisapprovalOfAmpleResourceConsumption"]
        elif deltaTimeToLive >= 3 and self.rules["agentOverconsumedResources"]:
            score -= self.rules["agentOverconsumedResources"]
            if self.rules["communityDisdainOfExtremeOverconsumption"]:
                score -= self.rules["communityDisdainOfExtremeOverconsumption"]
        return math.erf(score)

    def findCellEmotionalScore(self, cell):
        deltaTimeToLive = self.findTimeToLive(potentialCell=cell) - self.timeToLive
        score = 0
        if deltaTimeToLive > 1:
            score = score - self.timesOverharvested
            self.timesOverharvested += 1
        return math.erf(score)

    def findCellPhysicalScore(self):
        return math.erf(1 / self.timeToLive) if self.timeToLive > 0 else 1

    def findCellSimpleScore(self, cell):
        return abs(self.findTimeToLive(potentialCell=cell) - self.timeToLive)

    def findCellSocialScore(self, cell):
        deltaTimeToLive = self.findTimeToLive(potentialCell=cell) - self.timeToLive
        score = 0
        if deltaTimeToLive <= 1:
            score = 1
        elif deltaTimeToLive > 1 and deltaTimeToLive <= 2:
            score -= self.timeSeenOverconsuming
        elif deltaTimeToLive > 2:
            score -= self.timesSeenIndulging
        score *= self.socialPressure
        return math.erf(score)

    def findEthicalValueOfCell(self, cell):
        score = self.findCellSimpleScore(cell)
        if self.pecs == True:
            if self.totalMetabolism == 0:
                return 0
            physicalScore = self.findCellPhysicalScore()
            emotionalScore = self.findCellEmotionalScore(cell)
            cognitiveScore = self.findCellCognitiveScore(cell)
            socialScore = self.findCellSocialScore(cell)
            score = physicalScore + emotionalScore + cognitiveScore + socialScore
            # TODO: Improve fidelity to temperance as it relates to agent lives
            #print(f"Agent {self.ID} -> ({cell.x},{cell.y}): {score} = {physicalScore} + {emotionalScore} + {cognitiveScore} + {socialScore}")
        return score

    def findSimpleTemperanceBestEthicalCell(self, cells):
        bestCell = None
        numCells = len(cells)
        midpoint = math.floor(numCells / 2)
        virtueRoll = random.random()
        if virtueRoll < self.decisionModelFactor:
            bestCell = cells[0]["cell"]
            newTemperanceFactor = round(self.decisionModelFactor + self.dynamicDecisionModelFactor, 2)
            self.decisionModelFactor = newTemperanceFactor if newTemperanceFactor <= 1 else 1
        else:
            bestCell = cells[-1]["cell"]
            newTemperanceFactor = round(self.decisionModelFactor - self.dynamicDecisionModelFactor, 2)
            self.decisionModelFactor = newTemperanceFactor if newTemperanceFactor >= 0 else 0
        return bestCell

    def updateAgentSocialPressureAfterConsumption(self):
        if self.cell is None:
            return
        neighbors = len(self.findNeighborhood(self.cell))
        if neighbors == 0:
            return 0
        else:
            self.socialPressure += self.dynamicSocialPressureFactor
            return self.socialPressure

    def updateAgentTemperanceRules(self):
        neighbors = len(self.findNeighborhood(self.cell))
        if self.lastDeltaTimeToLive <= 1:
            # Consuming up to 1x metabolic need is good for the agent
            self.rules["agentConsumedAdequateResources"] += 1
        elif self.lastDeltaTimeToLive > 1 and self.lastDeltaTimeToLive <= 2:
            # Consuming 1-2x metabolic is is great for the agent
            self.rules["agentConsumedAmpleResources"] += 1
            # Consuming 1-2x metabolic need is overconsumption and is bad for the community
            if neighbors > 0:
                self.timeSeenOverconsuming += 1
                self.rules["communityDisapprovalOfAmpleResourceConsumption"] += 1
        elif self.lastDeltaTimeToLive > 2:
            # Consuming more than 2x metabolic need is bad for both the agent and the community
            self.rules["agentOverconsumedResources"] += 1
            if neighbors > 0:
                self.timesSeenIndulging += 1 
                self.rules["communityDisdainOfExtremeOverconsumption"] += 1

    def collectResourcesAtCell(self):
        self.lastDeltaTimeToLive = self.findTimeToLive(potentialCell=self.cell) - self.timeToLive
        super().collectResourcesAtCell()

    def doMetabolism(self):
        self.updateAgentSocialPressureAfterConsumption()
        super().doMetabolism()

    def updateValues(self):
        super().updateValues()
        self.updateAgentTemperanceRules()

    def spawnChild(self, childID, birthday, cell, configuration):
        return Temperance(childID, birthday, cell, configuration)

class Locke(agent.Agent):
    def __init__(self, agentID, birthday, cell, configuration):
        super().__init__(agentID, birthday, cell, configuration)
        self.locke = {"claims": [], "violations": [], "debtsReceivable": []}

    def cellOwner(self, cell):
        return getattr(cell, "owner", None)

    def cellConsentedAgents(self, cell):
        if not hasattr(cell, "consentedAgents"):
            cell.consentedAgents = set()
        return cell.consentedAgents

    def agentLandDebtsOwed(self, agent):
        if not hasattr(agent, "landDebtsOwed"):
            agent.landDebtsOwed = []
        return agent.landDebtsOwed

    def claimCellFor(self, cell, owner):
        cell.owner = owner
        cell.lastHarvestedTimestep = owner.timestep
        cell.consentedAgents = set()

    def forfeitCellClaim(self, cell):
        cell.owner = None
        cell.lastHarvestedTimestep = -1
        cell.consentedAgents = set()

    def convertViolationsToDebts(self, owner, cell, timestep):
        remainingViolations = []
        for violation in owner.locke["violations"]:
            if violation["cell"] != cell:
                remainingViolations.append(violation)
                continue
            trespasser = violation["trespasser"]
            debt = {"creditor": owner, "debtor": trespasser, "cell": cell,
                    "amount": violation["amount"], "createdTimestep": timestep}
            owner.locke["debtsReceivable"].append(debt)
            self.agentLandDebtsOwed(trespasser).append(debt)
            if "all" in owner.debug or "agent" in owner.debug:
                print(f"Agent {owner.ID} converts trespass by Agent {trespasser.ID} on ({cell.x},{cell.y}) into a debt of {round(debt['amount'], 2)}")
        owner.locke["violations"] = remainingViolations

    def removeSettledDebt(self, debt):
        creditor = debt["creditor"]
        debtor = debt["debtor"]
        if debt in creditor.locke["debtsReceivable"]:
            creditor.locke["debtsReceivable"].remove(debt)
        owedList = self.agentLandDebtsOwed(debtor)
        if debt in owedList:
            owedList.remove(debt)

    def transferLand(self, cell, previousOwner, newOwner):
        if cell in previousOwner.locke["claims"]:
            previousOwner.locke["claims"].remove(cell)
        self.convertViolationsToDebts(previousOwner, cell, previousOwner.timestep)
        self.claimCellFor(cell, newOwner)
        newOwner.locke["claims"].append(cell)

    def acquireLandClaim(self, cell):
        self.claimCellFor(cell, self)
        self.locke["claims"].append(cell)
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID} claims cell ({cell.x},{cell.y})")

    def collectResourcesAtCell(self):
        cell = self.cell
        sugarHarvested = cell.sugar
        spiceHarvested = cell.spice
        super().collectResourcesAtCell()

        owner = self.cellOwner(cell)
        if owner is None:
            nearbyCells = self.findCellsInRange(newCell=cell)
            unclaimedNearbyCellExists = any(self.cellOwner(nearby) is None for nearby in nearbyCells)
            if unclaimedNearbyCellExists:
                self.acquireLandClaim(cell)
        elif owner is self:
            self.processReturnToOwnedLand(cell)
        elif owner.isAlive() == True:
            cell.lastHarvestedTimestep = self.timestep
            if self not in self.cellConsentedAgents(cell):
                violation = {"trespasser": self, "cell": cell,
                             "amount": sugarHarvested + spiceHarvested, "timestep": self.timestep}
                owner.locke["violations"].append(violation)
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} trespasses on Agent {owner.ID}'s cell ({cell.x},{cell.y}), harvesting {round(violation['amount'], 2)}")

    def processReturnToOwnedLand(self, cell):
        cell.lastHarvestedTimestep = self.timestep
        self.convertViolationsToDebts(self, cell, self.timestep)
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID} returns to owned cell ({cell.x},{cell.y})")

    def processLandAbandonment(self):
        configuration = self.cell.environment.sugarscape.configuration
        decayThreshold = configuration["environmentLandDecayTimesteps"]
        stillOwned = []
        for claimedCell in self.locke["claims"]:
            if self.timestep - claimedCell.lastHarvestedTimestep >= decayThreshold:
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} forfeits abandoned cell ({claimedCell.x},{claimedCell.y}) after {self.timestep - claimedCell.lastHarvestedTimestep} timesteps")
                self.forfeitCellClaim(claimedCell)
                self.locke["violations"] = [v for v in self.locke["violations"] if v["cell"] != claimedCell]
            else:
                stillOwned.append(claimedCell)
        self.locke["claims"] = stillOwned

    def settleDebtsVoluntarily(self):
        for debt in list(self.agentLandDebtsOwed(self)):
            creditor = debt["creditor"]
            if creditor.isAlive() == False:
                self.removeSettledDebt(debt)
                continue
            availableSugar = max(0, self.sugar - self.findSugarMetabolism())
            availableSpice = max(0, self.spice - self.findSpiceMetabolism())
            payment = min(debt["amount"], availableSugar + availableSpice)
            if payment <= 0:
                continue
            sugarPayment = min(availableSugar, payment)
            spicePayment = payment - sugarPayment
            self.sugar -= sugarPayment
            self.spice -= spicePayment
            creditor.sugar += sugarPayment
            creditor.spice += spicePayment
            debt["amount"] -= payment
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} voluntarily repays {round(payment, 2)} of land debt to Agent {creditor.ID} ({round(debt['amount'], 2)} remaining)")
            if debt["amount"] <= 0:
                self.removeSettledDebt(debt)

    def doLandConsentGrants(self):
        for claimedCell in self.locke["claims"]:
            fee = claimedCell.sugar + claimedCell.spice
            if fee <= 0:
                continue
            consented = self.cellConsentedAgents(claimedCell)
            for candidate in claimedCell.findNeighborAgents():
                if candidate is self or candidate in consented or candidate.isAlive() == False:
                    continue
                availableSugar = max(0, candidate.sugar - 50 * candidate.findSugarMetabolism())
                availableSpice = max(0, candidate.spice - 50 * candidate.findSpiceMetabolism())
                if availableSugar + availableSpice < fee:
                    continue
                sugarPayment = min(availableSugar, fee)
                spicePayment = fee - sugarPayment
                candidate.sugar -= sugarPayment
                candidate.spice -= spicePayment
                self.sugar += sugarPayment
                self.spice += spicePayment
                consented.add(candidate)
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} grants land consent on ({claimedCell.x},{claimedCell.y}) to Agent {candidate.ID} for fee {round(fee, 2)}")

    def doLandBuyoutOffers(self):
        for neighborCell in self.cell.neighbors.values():
            owner = self.cellOwner(neighborCell)
            if owner is None or owner is self or owner.isAlive() == False:
                continue
            if neighborCell == owner.cell or neighborCell in owner.cellsInRange:
                continue
            price = neighborCell.maxSugar + neighborCell.maxSpice
            if price <= 0:
                continue
            availableSugar = max(0, self.sugar - 50 * self.findSugarMetabolism())
            availableSpice = max(0, self.spice - 50 * self.findSpiceMetabolism())
            if availableSugar + availableSpice < price:
                continue
            sugarPayment = min(availableSugar, price)
            spicePayment = price - sugarPayment
            self.sugar -= sugarPayment
            self.spice -= spicePayment
            owner.sugar += sugarPayment
            owner.spice += spicePayment
            self.transferLand(neighborCell, owner, self)
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} buys out Agent {owner.ID}'s cell ({neighborCell.x},{neighborCell.y}) for {round(price, 2)}")

    def doForcefulDebtCollection(self):
        for neighbor in self.cell.findNeighborAgents():
            if neighbor is self or neighbor.isAlive() == False or not isinstance(neighbor, Locke):
                continue
            for debt in list(self.agentLandDebtsOwed(neighbor)):
                if self.timestep - debt["createdTimestep"] < 5:
                    continue
                creditor = debt["creditor"]
                if creditor.isAlive() == False:
                    self.removeSettledDebt(debt)
                    continue
                availableSugar = max(0, neighbor.sugar)
                availableSpice = max(0, neighbor.spice)
                seizure = min(debt["amount"], availableSugar + availableSpice)
                if seizure <= 0:
                    continue
                seizeSugar = min(availableSugar, seizure)
                seizeSpice = seizure - seizeSugar
                neighbor.sugar -= seizeSugar
                neighbor.spice -= seizeSpice
                creditor.sugar += seizeSugar
                creditor.spice += seizeSpice
                debt["amount"] -= seizure
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} forcefully collects {round(seizure, 2)} from Agent {neighbor.ID} on behalf of Agent {creditor.ID} ({round(debt['amount'], 2)} remaining)")
                if debt["amount"] <= 0:
                    self.removeSettledDebt(debt)

    def doTrading(self):
        super().doTrading()
        self.doLandConsentGrants()
        self.doLandBuyoutOffers()
        self.doForcefulDebtCollection()

    def findBestEthicalCell(self, cells, greedyBestCell=None):
        if len(cells) == 0:
            return None
        if "all" in self.debug or "agent" in self.debug:
            self.printCellScores(cells)
        for cellRecord in cells:
            cellRecord["wealth"] = self.findEthicalValueOfCell(cellRecord["cell"])
        cells = self.sortCellsByWealth(cells)
        bestCell = cells[0]["cell"]
        if "all" in self.debug or "agent" in self.debug:
            self.printEthicalCellScores(cells)
            print(f"Agent {self.ID} selects best ethical cell ({bestCell.x},{bestCell.y})")
        return bestCell

    def findEthicalValueOfCell(self, cell):
        cellValue = cell.sugar + cell.spice
        owner = self.cellOwner(cell)
        if owner is not None and owner is not self and owner.isAlive() == True and self not in self.cellConsentedAgents(cell):
            cellValue *= 1.0
        return cellValue

    def doInheritance(self):
        super().doInheritance()
        livingLockeChildren = [c for c in self.socialNetwork["children"] if c.isAlive() == True and isinstance(c, Locke)]
        for claimedCell in list(self.locke["claims"]):
            if len(livingLockeChildren) > 0:
                heir = random.choice(livingLockeChildren)
                self.transferLand(claimedCell, self, heir)
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} bequeaths cell ({claimedCell.x},{claimedCell.y}) to Agent {heir.ID}")
            else:
                self.forfeitCellClaim(claimedCell)
                self.locke["claims"].remove(claimedCell)
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} dies without Locke heirs; cell ({claimedCell.x},{claimedCell.y}) reverts to unclaimed")
        for debt in list(self.locke["debtsReceivable"]):
            self.removeSettledDebt(debt)
        for debt in list(self.agentLandDebtsOwed(self)):
            self.removeSettledDebt(debt)

    def updateValues(self):
        super().updateValues()
        self.processLandAbandonment()
        self.settleDebtsVoluntarily()

    def spawnChild(self, childID, birthday, cell, configuration):
        return Locke(childID, birthday, cell, configuration)
