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
        scenarioConfiguration = cell.environment.sugarscape.configuration
        thresholdRange = scenarioConfiguration["environmentLandTrustThresholdRange"]
        self.locke = {"claims": [], "debtsReceivable": [], "trust": {},
                       "trustThreshold": random.randint(thresholdRange[0], thresholdRange[1]),
                       "government": None, "governmentRate": None, "restrained": False,
                       "governmentRedistribution": None,
                       "grievance": 0.0, "lastHarvest": 0.0, "lastLevyTimestep": -1,
                       "governmentExecutor": None, "executorGrievance": 0.0,
                       "governmentExecutorPay": None, "governmentForm": None,
                       "governmentLegislature": None, "governmentLevyFraction": None,
                       "lastLegislativeReviewTimestep": None, "legislatureGrievance": 0.0}

    def spawnChild(self, childID, birthday, cell, configuration):
        return Locke(childID, birthday, cell, configuration)

    def doGovernment(self):
        self.doForcefulDebtCollection()
        self.doTrustAccrual()
        self.doGovernanceReview()

    def doProperty(self):
        self.processLandAbandonment()
        self.settleDebtsVoluntarily()

    def recordLandTrespassIfOwned(self, sugarCollected, spiceCollected):
        owners = getattr(self.cell, "owners", None)
        if not owners or self in owners or not any(owner.isAlive() == True for owner in owners):
            return
        if not hasattr(self.cell, "pendingViolations"):
            self.cell.pendingViolations = []
        self.cell.pendingViolations.append({"trespasser": self, "cell": self.cell,
                                             "amount": sugarCollected + spiceCollected,
                                             "timestep": self.timestep, "owners": dict(owners)})
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID} trespasses on claimed cell ({self.cell.x},{self.cell.y}), harvesting {round(sugarCollected + spiceCollected, 2)}")
        for other in self.cell.findNeighborAgents():
            if hasattr(other, "resetTrustIn"):
                other.resetTrustIn(self)

    def findBestEthicalCell(self, cells, greedyBestCell=None):
        if len(cells) == 0:
            return None
        pursuitTarget = self.findEnforcementTarget()
        if "all" in self.debug or "agent" in self.debug:
            self.printCellScores(cells)
        for cellRecord in cells:
            cellRecord["wealth"] = self.findEthicalValueOfCell(cellRecord["cell"], pursuitTarget)
        cells = self.sortCellsByWealth(cells)
        bestCell = cells[0]["cell"]
        if "all" in self.debug or "agent" in self.debug:
            self.printEthicalCellScores(cells)
            print(f"Agent {self.ID} selects best ethical cell ({bestCell.x},{bestCell.y})")
        return bestCell

    def findEnforcementTarget(self):
        executor = self.locke["governmentExecutor"]
        if executor is None or self not in executor:
            return None
        government = self.locke["government"] or {self}
        collectible = [debt for member in government for debt in member.locke["debtsReceivable"]
                       if debt["debtor"].isAlive()
                       and debt["debtor"].sugar + debt["debtor"].spice > 0]
        if len(collectible) == 0:
            return None
        return min(collectible, key=lambda debt: debt["createdTimestep"])["debtor"]

    def findExpectedViolationCost(self, cell, owners):
        configuration = self.cell.environment.sugarscape.configuration
        representative = next(iter(owners))
        representativeLocke = getattr(representative, "locke", None)
        government = representativeLocke.get("government") if representativeLocke is not None else None
        rate = representativeLocke.get("governmentRate") if representativeLocke is not None else None
        if rate is None:
            rate = min(configuration["environmentLandReparationRateChoices"])
        return (configuration["environmentLandOwnerCountCostWeight"] * len(owners)
                + configuration["environmentLandGovernmentCostWeight"] * (1 if government is not None else 0)
                + configuration["environmentLandReparationRateCostWeight"] * rate
                + configuration["environmentLandRestrainedCostWeight"] * (1 if self.locke["restrained"] == True else 0))

    def findEthicalValueOfCell(self, cell, pursuitTarget=None):
        cellValue = cell.sugar + cell.spice
        owners = self.cellOwners(cell)
        if len(owners) > 0 and self not in owners and any(owner.isAlive() == True for owner in owners):
            cellValue = cellValue - self.findExpectedViolationCost(cell, owners)
        if pursuitTarget is not None:
            configuration = self.cell.environment.sugarscape.configuration
            weight = configuration["environmentLandExecutorPursuitWeight"]
            distance = abs(cell.x - pursuitTarget.cell.x) + abs(cell.y - pursuitTarget.cell.y)
            cellValue -= weight * distance
        return cellValue

    def cellOwners(self, cell):
        if not hasattr(cell, "owners"):
            cell.owners = {}
        return cell.owners

    def claimCellFor(self, cell, owner):
        cell.owners = {owner: 1.0}
        cell.lastHarvestedTimestep = owner.timestep

    def acquireLandClaim(self, cell):
        self.claimCellFor(cell, self)
        self.locke["claims"].append(cell)
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID} claims cell ({cell.x},{cell.y})")

    def collectResourcesAtCell(self):
        cell = self.cell
        sugarCollected = cell.sugar
        spiceCollected = cell.spice
        harvested = sugarCollected + spiceCollected
        self.locke["lastHarvest"] = harvested
        super().collectResourcesAtCell()
        self.recordLandTrespassIfOwned(sugarCollected, spiceCollected)
        if harvested <= 0:
            return

        owners = self.cellOwners(cell)
        if len(owners) == 0:
            configuration = self.cell.environment.sugarscape.configuration
            maxClaims = configuration["environmentLandMaxClaimsPerAgent"]
            if len(self.locke["claims"]) < maxClaims and self.leavesEnoughForNeighbors(cell):
                self.acquireLandClaim(cell)
        elif self in owners:
            self.processReturnToOwnedLand(cell)

    def leavesEnoughForNeighbors(self, cell):
        ranges = [self.findCellsInRange(newCell=cell)]
        ranges += [neighbor.findCellsInRange() for neighbor in self.cell.findNeighborAgents()]
        for cellsInRange in ranges:
            if not any(candidate is not cell and len(self.cellOwners(candidate)) == 0
                       for candidate in cellsInRange):
                return False
        return True

    def processReturnToOwnedLand(self, cell):
        cell.lastHarvestedTimestep = self.timestep
        self.convertViolationsToDebts(cell, self.timestep)
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID} returns to co-owned cell ({cell.x},{cell.y})")

    def processLandAbandonment(self):
        configuration = self.cell.environment.sugarscape.configuration
        decayThreshold = configuration["environmentLandDecayTimesteps"]
        stillOwned = []
        for claimedCell in self.locke["claims"]:
            owners = self.cellOwners(claimedCell)
            if self not in owners:
                continue
            if self.timestep - claimedCell.lastHarvestedTimestep >= decayThreshold:
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} forfeits abandoned cell ({claimedCell.x},{claimedCell.y}) after {self.timestep - claimedCell.lastHarvestedTimestep} timesteps")
                self.forfeitCellClaim(claimedCell)
            else:
                stillOwned.append(claimedCell)
        self.locke["claims"] = stillOwned

    def forfeitCellClaim(self, cell):
        cell.owners = {}
        cell.lastHarvestedTimestep = -1

    def doInheritance(self):
        super().doInheritance()
        livingLockeChildren = [c for c in self.socialNetwork["children"] if c.isAlive() == True and isinstance(c, Locke)]
        for claimedCell in list(self.locke["claims"]):
            owners = self.cellOwners(claimedCell)
            if self not in owners:
                self.locke["claims"].remove(claimedCell)
                continue
            if len(livingLockeChildren) > 0:
                self.convertViolationsToDebts(claimedCell, self.timestep)
                myShare = owners.pop(self)
                perChildShare = myShare / len(livingLockeChildren)
                for child in livingLockeChildren:
                    owners[child] = owners.get(child, 0) + perChildShare
                    if claimedCell not in child.locke["claims"]:
                        child.locke["claims"].append(claimedCell)
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} bequeaths {round(myShare * 100, 1)}% share of cell ({claimedCell.x},{claimedCell.y}) split among {len(livingLockeChildren)} children")
            else:
                del owners[self]
                if "all" in self.debug or "agent" in self.debug:
                    print(f"Agent {self.ID} dies without Locke heirs; share of cell ({claimedCell.x},{claimedCell.y}) reverts to unclaimed")
            if len(owners) == 0:
                self.forfeitCellClaim(claimedCell)
            self.locke["claims"].remove(claimedCell)
        for debt in list(self.locke["debtsReceivable"]):
            self.removeSettledDebt(debt)
        for debt in list(self.agentLandDebtsOwed(self)):
            self.removeSettledDebt(debt)
        government = self.locke["government"]
        if government is not None:
            government.discard(self)
            self.dissolveGovernmentIfUnviable(government)
            if len(government) >= 2:
                survivor = next(iter(government))
                survivor.reviewLegislature(government)
                survivor.reviewRedistribution(government)
                survivor.reviewExecutor(government)
                survivor.reviewExecutorPay(government)
                survivor.reviewLevyFraction(government)
                for member in government:
                    member.locke["lastLegislativeReviewTimestep"] = survivor.timestep
                    member.locke["legislatureGrievance"] = 0.0

    def cellPendingViolations(self, cell):
        if not hasattr(cell, "pendingViolations"):
            cell.pendingViolations = []
        return cell.pendingViolations

    def convertViolationsToDebts(self, cell, timestep):
        choices = cell.environment.sugarscape.configuration["environmentLandReparationRateChoices"]
        for violation in self.cellPendingViolations(cell):
            trespasser = violation["trespasser"]
            wrongedOwners = violation.get("owners") or self.cellOwners(cell)
            for owner, share in wrongedOwners.items():
                if owner is trespasser or owner.isAlive() == False:
                    continue
                rate = owner.locke.get("governmentRate")
                if rate is None:
                    rate = min(choices)
                debtAmount = violation["amount"] * share * rate
                if debtAmount <= 0:
                    continue
                debt = {"creditor": owner, "debtor": trespasser, "cell": cell,
                        "amount": debtAmount, "createdTimestep": timestep,
                        "executorRecognized": False}
                owner.locke["debtsReceivable"].append(debt)
                self.agentLandDebtsOwed(trespasser).append(debt)
                if hasattr(owner, "resetTrustIn"):
                    owner.resetTrustIn(trespasser)
                if "all" in owner.debug or "agent" in owner.debug:
                    print(f"Agent {owner.ID} converts trespass by Agent {trespasser.ID} on ({cell.x},{cell.y}) into a debt of {round(debtAmount, 2)} ({round(share * 100, 1)}% share)")
        cell.pendingViolations = []

    def agentLandDebtsOwed(self, agent):
        if not hasattr(agent, "landDebtsOwed"):
            agent.landDebtsOwed = []
        return agent.landDebtsOwed

    def removeSettledDebt(self, debt):
        creditor = debt["creditor"]
        debtor = debt["debtor"]
        if debt in creditor.locke["debtsReceivable"]:
            creditor.locke["debtsReceivable"].remove(debt)
        owedList = self.agentLandDebtsOwed(debtor)
        if debt in owedList:
            owedList.remove(debt)

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

    def doForcefulDebtCollection(self):
        configuration = self.cell.environment.sugarscape.configuration
        for neighbor in self.cell.findNeighborAgents():
            if neighbor is self or neighbor.isAlive() == False:
                continue
            for debt in list(self.agentLandDebtsOwed(neighbor)):
                creditor = debt["creditor"]
                if creditor.isAlive() == False:
                    self.removeSettledDebt(debt)
                    continue
                government = self.locke["government"]
                executor = self.locke["governmentExecutor"]
                selfIsExecutor = executor is not None and self in executor
                creditorIsFellowMember = government is not None and creditor in government
                assisting = False
                if creditor is self:
                    if selfIsExecutor:
                        debt["executorRecognized"] = True
                elif creditorIsFellowMember and selfIsExecutor:
                    debt["executorRecognized"] = True
                elif creditorIsFellowMember and executor is not None and debt.get("executorRecognized") == True:
                    assisting = True
                else:
                    if "all" in self.debug or "agent" in self.debug:
                        target = "the executor" if creditorIsFellowMember else "its creditor"
                        print(f"Agent {self.ID} leaves Agent {neighbor.ID}'s debt to Agent "
                              f"{creditor.ID} to {target}")
                    continue
                sugarRecovered, spiceRecovered = self.doSteal(neighbor.cell, debt["amount"])
                recovered = sugarRecovered + spiceRecovered
                if recovered <= 0:
                    continue
                if creditor is not self:
                    self.sugar -= sugarRecovered
                    self.spice -= spiceRecovered
                    creditor.sugar += sugarRecovered
                    creditor.spice += spiceRecovered
                debt["amount"] -= recovered
                if "all" in self.debug or "agent" in self.debug:
                    role = " (assisting the executor, Sect. 130)" if assisting else ""
                    print(f"Agent {self.ID} forcefully steals {round(recovered, 2)} from Agent {neighbor.ID} on behalf of Agent {creditor.ID}{role} ({round(debt['amount'], 2)} remaining)")
                if creditor is self and government is not None and selfIsExecutor:
                    partialityPenalty = configuration["environmentLandExecutorPartialityPenalty"]
                    for member in government:
                        if member is self:
                            continue
                        if any(d["debtor"].isAlive()
                               and d["debtor"].sugar + d["debtor"].spice > 0 for d in member.locke["debtsReceivable"]):
                            member.locke["grievance"] += partialityPenalty
                            if "all" in self.debug or "agent" in self.debug:
                                print(f"Agent {self.ID} the executor collects its own debt while Agent {member.ID}'s goes unreached (Sect. 156)")
                if isinstance(neighbor, Locke) and neighbor.locke["restrained"] == False:
                    neighbor.locke["restrained"] = True
                    if "all" in neighbor.debug or "agent" in neighbor.debug:
                        print(f"Agent {neighbor.ID} is restrained after being stolen from and will avoid claimed land")
                if debt["amount"] <= 0:
                    self.removeSettledDebt(debt)

    def findQuantileChoice(self, member, choices, referenceGroup):
        sortedClaims = sorted(len(m.locke["claims"]) for m in referenceGroup)
        n = len(sortedClaims)
        claims = len(member.locke["claims"])
        for k in range(1, len(choices)):
            position = (k / len(choices)) * (n - 1)
            lowerIndex = int(position)
            upperIndex = min(n - 1, lowerIndex + 1)
            breakpoint = sortedClaims[lowerIndex] + (position - lowerIndex) * (sortedClaims[upperIndex] - sortedClaims[lowerIndex])
            if claims <= breakpoint:
                return choices[k - 1]
        return choices[-1]

    def voteByQuantileBracket(self, voters, choices, referenceGroup):
        preferred = sorted((self.findQuantileChoice(member, choices, referenceGroup) for member in voters),
                            key=choices.index)
        return preferred[(len(preferred) - 1) // 2]

    def voteReparationRate(self, founders):
        configuration = self.cell.environment.sugarscape.configuration
        choices = sorted(configuration["environmentLandReparationRateChoices"])
        return self.voteByQuantileBracket(founders, choices, founders)

    def doTrustAccrual(self):
        for claimedCell in self.locke["claims"]:
            owners = self.cellOwners(claimedCell)
            if self not in owners:
                continue
            thisTimestepTrespassers = {v["trespasser"] for v in self.cellPendingViolations(claimedCell)
                                        if v["timestep"] == self.timestep}
            for candidate in claimedCell.findNeighborAgents():
                if candidate is self or candidate in owners or candidate.isAlive() == False:
                    continue
                if candidate in thisTimestepTrespassers:
                    continue
                self.increaseTrust(candidate, claimedCell)

    def increaseTrust(self, candidate, cell):
        trust = self.locke["trust"]
        trust[candidate.ID] = trust.get(candidate.ID, 0) + 1
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID} gains 1 trust point toward Agent {candidate.ID} for not stealing near "
                  f"cell ({cell.x},{cell.y}) (trust {trust[candidate.ID]}/{self.locke['trustThreshold']})")
        if isinstance(candidate, Locke):
            self.attemptGovernmentFormation(candidate)

    def resetTrustIn(self, violator):
        if self.locke["trust"].get(violator.ID, 0) != 0:
            self.locke["trust"][violator.ID] = 0
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID}'s trust in Agent {violator.ID} resets to 0 after Agent {violator.ID}'s violation")

    def attemptGovernmentFormation(self, other):
        if self.locke["trust"].get(other.ID, 0) < self.locke["trustThreshold"]:
            return
        selfGovernment = self.locke["government"]
        otherGovernment = other.locke["government"]
        if selfGovernment is not None:
            return
        if otherGovernment is not None:
            self.addToGovernment(otherGovernment, self)
            return
        if other.locke["trust"].get(self.ID, 0) < other.locke["trustThreshold"]:
            return
        newGovernment = {self, other}
        founders = [self, other]
        configuration = self.cell.environment.sugarscape.configuration
        formVote = self.voteGovernmentForm(founders)
        if formVote == "restricted" and configuration["environmentLandLegislatureSize"] != "all":
            legislatureSize = min(max(1, configuration["environmentLandLegislatureSize"]), len(founders))
            form = "monarchy" if legislatureSize == 1 else "oligarchy"
        else:
            form = "democracy"
        legislature = self.findLegislature(founders, form)
        rate = self.voteReparationRate(legislature)
        redistribution = self.voteRedistribution(legislature, founders)
        executor = self.voteExecutor(legislature)
        pay = self.votePayFraction(legislature, executor)
        levyFraction = self.voteLevyFraction(legislature, founders)
        for founder in founders:
            founder.locke["government"] = newGovernment
            founder.locke["governmentForm"] = form
            founder.locke["governmentLegislature"] = legislature
            founder.locke["governmentRate"] = rate
            founder.locke["governmentRedistribution"] = redistribution
            founder.locke["governmentExecutor"] = executor
            founder.locke["governmentExecutorPay"] = pay
            founder.locke["governmentLevyFraction"] = levyFraction
            founder.locke["lastLegislativeReviewTimestep"] = self.timestep
            founder.locke["grievance"] = 0.0
            founder.locke["executorGrievance"] = 0.0
        if "all" in self.debug or "agent" in self.debug:
            executorIDs = sorted(member.ID for member in executor)
            legislatureIDs = sorted(member.ID for member in legislature)
            print(f"Agent {self.ID} and Agent {other.ID} found a new {form} government "
                  f"(legislature {legislatureIDs}, reparation rate {rate}, "
                  f"redistribution {redistribution}, executor(s) {executorIDs}, executor pay {pay}, "
                  f"levy fraction {levyFraction}) after mutual trust crosses both thresholds")

    def voteGovernmentForm(self, founders):
        configuration = self.cell.environment.sugarscape.configuration
        reference = configuration["environmentLandReparationStakeReference"]
        preferred = ["restricted" if reference > 0 and len(f.locke["claims"]) >= reference
                     else "democracy" for f in founders]
        order = ["democracy", "restricted"]
        preferred.sort(key=order.index)
        return preferred[(len(preferred) - 1) // 2]

    def findLegislature(self, members, form):
        configuration = self.cell.environment.sugarscape.configuration
        if form == "democracy" or configuration["environmentLandLegislatureSize"] == "all":
            return frozenset(members)
        size = min(max(1, configuration["environmentLandLegislatureSize"]), len(members))
        ranked = sorted(members, key=lambda member: (len(member.locke["claims"]), -member.ID), reverse=True)
        return frozenset(ranked[:size])

    def reviewLegislature(self, government):
        members = list(government)
        if len(members) < 2:
            return False
        form = members[0].locke["governmentForm"]
        newLegislature = self.findLegislature(members, form)
        if newLegislature == members[0].locke["governmentLegislature"]:
            return False
        for member in members:
            member.locke["governmentLegislature"] = newLegislature
        if "all" in self.debug or "agent" in self.debug:
            legislatureIDs = sorted(member.ID for member in newLegislature)
            print(f"Agent {self.ID}'s government revises its legislature to {legislatureIDs}")
        return True

    def addToGovernment(self, government, newMember):
        government.add(newMember)
        newMember.locke["government"] = government
        existingMember = next(member for member in government if member is not newMember)
        newMember.locke["governmentRate"] = existingMember.locke["governmentRate"]
        newMember.locke["governmentRedistribution"] = existingMember.locke["governmentRedistribution"]
        newMember.locke["governmentExecutor"] = existingMember.locke["governmentExecutor"]
        newMember.locke["governmentExecutorPay"] = existingMember.locke["governmentExecutorPay"]
        newMember.locke["governmentForm"] = existingMember.locke["governmentForm"]
        newMember.locke["governmentLegislature"] = existingMember.locke["governmentLegislature"]
        newMember.locke["governmentLevyFraction"] = existingMember.locke["governmentLevyFraction"]
        newMember.locke["lastLegislativeReviewTimestep"] = existingMember.locke["lastLegislativeReviewTimestep"]
        newMember.locke["grievance"] = 0.0
        newMember.locke["executorGrievance"] = 0.0
        if "all" in self.debug or "agent" in self.debug:
            memberIDs = sorted(member.ID for member in government)
            print(f"Agent {newMember.ID} joins an existing government (no re-founding, members: {memberIDs})")

    def voteExecutor(self, members):
        configuration = self.cell.environment.sugarscape.configuration
        count = min(max(1, configuration["environmentLandExecutorCount"]), len(members))
        ranked = sorted(members, key=lambda member: (member.findVision() + member.findMovement(), -member.ID), reverse=True)
        return frozenset(ranked[:count])

    def reviewExecutor(self, government):
        members = list(government)
        if len(members) < 2:
            return False
        legislature = members[0].locke["governmentLegislature"]
        newExecutor = self.voteExecutor(legislature)
        if newExecutor == members[0].locke["governmentExecutor"]:
            return False
        for member in members:
            member.locke["governmentExecutor"] = newExecutor
        if "all" in self.debug or "agent" in self.debug:
            executorIDs = sorted(member.ID for member in newExecutor)
            print(f"Agent {self.ID}'s government re-appoints Agent(s) {executorIDs} as executor (Sect. 152)")
        return True

    def votePayFraction(self, members, executor):
        configuration = self.cell.environment.sugarscape.configuration
        choices = sorted(configuration["environmentLandExecutorPayChoices"])
        preferred = [choices[-1] if member in executor else choices[0] for member in members]
        preferred.sort()
        return preferred[(len(preferred) - 1) // 2]

    def reviewExecutorPay(self, government):
        members = list(government)
        if len(members) < 2:
            return False
        legislature = members[0].locke["governmentLegislature"]
        executor = members[0].locke["governmentExecutor"] or frozenset()
        newPay = self.votePayFraction(legislature, executor)
        if newPay == members[0].locke["governmentExecutorPay"]:
            return False
        for member in members:
            member.locke["governmentExecutorPay"] = newPay
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID}'s government revises executor pay to {newPay} (Sect. 140/138)")
        return True

    def voteRedistribution(self, votingMembers, allMembers):
        meanClaims = sum(len(member.locke["claims"]) for member in allMembers) / len(allMembers)
        votes = ["proportional" if len(member.locke["claims"]) > meanClaims else "equal" for member in votingMembers]
        return "proportional" if votes.count("proportional") > votes.count("equal") else "equal"

    def voteLevyFraction(self, legislature, allMembers):
        configuration = self.cell.environment.sugarscape.configuration
        choices = sorted(configuration["environmentLandLevyFractionChoices"])
        return self.voteByQuantileBracket(legislature, choices, allMembers)

    def reviewLevyFraction(self, government):
        members = list(government)
        if len(members) < 2:
            return False
        legislature = members[0].locke["governmentLegislature"]
        newFraction = self.voteLevyFraction(legislature, members)
        if newFraction == members[0].locke["governmentLevyFraction"]:
            return False
        for member in members:
            member.locke["governmentLevyFraction"] = newFraction
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID}'s government revises the levy fraction to {newFraction} (Sect. 138/140)")
        return True

    def runLevyPass(self, government):
        members = [member for member in government if member.locke["lastLevyTimestep"] != self.timestep]
        if len(members) < len(government) or len(members) < 2:
            return
        for member in members:
            member.locke["lastLevyTimestep"] = self.timestep
        configuration = self.cell.environment.sugarscape.configuration
        fraction = members[0].locke["governmentLevyFraction"]
        levy = fraction * (sum(m.locke["lastHarvest"] for m in members) / len(members))
        paid = {}
        for member in members:
            due = min(levy, max(0.0, member.sugar) + max(0.0, member.spice))
            fromSugar = min(max(0.0, member.sugar), due)
            member.sugar -= fromSugar
            member.spice -= due - fromSugar
            paid[member] = due
        pool = sum(paid.values())
        executors = members[0].locke["governmentExecutor"] or frozenset()
        payFraction = members[0].locke["governmentExecutorPay"]
        executorPay = pool * payFraction if len(executors) > 0 else 0.0
        if executorPay > 0:
            perExecutor = executorPay / len(executors)
            for executor in executors:
                executor.sugar += perExecutor
        remainingPool = pool - executorPay
        scale = (remainingPool / pool) if pool > 0 else 0.0
        maintenance = configuration["environmentLandExecutorMaintenanceFraction"]
        excess = max(0.0, payFraction - maintenance) * pool
        redistribution = members[0].locke["governmentRedistribution"]
        isDemocracy = members[0].locke["governmentForm"] == "democracy"
        legislature = members[0].locke["governmentLegislature"]
        totalClaims = sum(len(m.locke["claims"]) for m in members)
        payoutTotalClaims = totalClaims if isDemocracy else sum(len(m.locke["claims"]) for m in legislature)
        for member in members:
            if not isDemocracy and member not in legislature:
                received = 0.0
            elif redistribution == "proportional" and payoutTotalClaims > 0:
                received = remainingPool * (len(member.locke["claims"]) / payoutTotalClaims)
            elif redistribution == "proportional":
                received = remainingPool / (len(members) if isDemocracy else len(legislature))
            elif isDemocracy:
                received = paid[member] * scale
            else:
                received = remainingPool / len(legislature)
            member.sugar += received
            fairBaseline = paid[member] * scale
            net = received - fairBaseline
            member.locke["grievance"] = max(0.0, member.locke["grievance"] - net)
            if excess > 0 and pool > 0:
                member.locke["grievance"] += excess * (paid[member] / pool)
            if not isDemocracy and member not in legislature:
                member.locke["legislatureGrievance"] += configuration["environmentLandLegislatureGrievancePenalty"]

    def reviewRedistribution(self, government):
        members = list(government)
        if len(members) < 2:
            return False
        legislature = members[0].locke["governmentLegislature"]
        newRule = self.voteRedistribution(legislature, members)
        if newRule == members[0].locke["governmentRedistribution"]:
            return False
        for member in members:
            member.locke["governmentRedistribution"] = newRule
        if "all" in self.debug or "agent" in self.debug:
            print(f"Agent {self.ID}'s government re-legislates redistribution to {newRule} (Sect. 153)")
        return True

    def doGovernanceReview(self):
        government = self.locke["government"]
        if government is None:
            return
        self.runLevyPass(government)
        configuration = self.cell.environment.sugarscape.configuration
        if self.locke["governmentExecutor"] is None or self not in self.locke["governmentExecutor"]:
            penalty = configuration["environmentLandExecutorNeglectPenalty"]
            unenforced = sum(1 for debt in self.locke["debtsReceivable"]
                             if debt["debtor"].isAlive()
                             and debt["debtor"].sugar + debt["debtor"].spice > 0)
            if unenforced > 0:
                self.locke["executorGrievance"] += penalty * unenforced

        if self.locke["grievance"] > configuration["environmentLandGrievanceThreshold"]:
            if "all" in self.debug or "agent" in self.debug:
                print(f"Agent {self.ID} withdraws consent from its government after a long train of abuses (Sect. 240)")
            government.discard(self)
            self.locke["government"] = None
            self.locke["governmentRate"] = None
            self.locke["governmentRedistribution"] = None
            self.locke["governmentExecutor"] = None
            self.locke["governmentExecutorPay"] = None
            self.locke["governmentForm"] = None
            self.locke["governmentLegislature"] = None
            self.locke["governmentLevyFraction"] = None
            self.locke["lastLegislativeReviewTimestep"] = None
            self.locke["grievance"] = 0.0
            self.locke["executorGrievance"] = 0.0
            self.locke["legislatureGrievance"] = 0.0
            self.dissolveGovernmentIfUnviable(government)
            if len(government) >= 2:
                survivor = next(iter(government))
                survivor.reviewLegislature(government)
                survivor.reviewExecutor(government)
                survivor.reviewExecutorPay(government)
                survivor.reviewLevyFraction(government)
                for member in government:
                    member.locke["lastLegislativeReviewTimestep"] = self.timestep
                    member.locke["legislatureGrievance"] = 0.0
            return
        legislatureGrievanceThreshold = configuration["environmentLandLegislatureGrievanceThreshold"]
        reconvene = sum(member.locke["legislatureGrievance"] for member in government) > legislatureGrievanceThreshold
        if not reconvene:
            interval = configuration["environmentLandLegislativeReviewInterval"]
            reconvene = self.timestep - self.locke["lastLegislativeReviewTimestep"] >= interval
        if reconvene:
            self.reviewLegislature(government)
            if self.reviewRedistribution(government):
                decay = configuration["environmentLandGrievanceDecay"]
                for member in government:
                    member.locke["grievance"] *= decay
            if self.reviewExecutor(government):
                for member in government:
                    member.locke["executorGrievance"] = 0.0
            self.reviewExecutorPay(government)
            self.reviewLevyFraction(government)
            for member in government:
                member.locke["lastLegislativeReviewTimestep"] = self.timestep
                member.locke["legislatureGrievance"] = 0.0

    def dissolveGovernmentIfUnviable(self, government):
        if government is None or len(government) >= 2:
            return
        for survivor in list(government):
            survivor.locke["government"] = None
            survivor.locke["governmentRate"] = None
            survivor.locke["governmentRedistribution"] = None
            survivor.locke["governmentExecutor"] = None
            survivor.locke["governmentExecutorPay"] = None
            survivor.locke["governmentForm"] = None
            survivor.locke["governmentLegislature"] = None
            survivor.locke["governmentLevyFraction"] = None
            survivor.locke["lastLegislativeReviewTimestep"] = None
            survivor.locke["grievance"] = 0.0
            survivor.locke["executorGrievance"] = 0.0
            survivor.locke["legislatureGrievance"] = 0.0
            if "all" in survivor.debug or "agent" in survivor.debug:
                print(f"Agent {survivor.ID}'s government dissolves - fewer than two members remain (Sect. 211)")
        government.clear()
