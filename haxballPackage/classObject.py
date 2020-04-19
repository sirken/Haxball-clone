import json
import math
import numpy as np
import haxballPackage.utilsHaxBall as utilsHax
import haxballPackage.functions as fnHax

haxVal = utilsHax.haxballVal

class Disc:
    def __init__(self, disc):
        if (disc.get("radius") != None):
            self.radius = disc["radius"]

        if (disc.get("bCoef") != None):
            self.bCoef = disc["bCoef"]

        if (disc.get("invMass") != None):
            self.invMass = disc["invMass"]

        if (disc.get("damping") != None):
            self.damping = disc["damping"]

        self.x = disc["pos"][0]
        self.y = disc["pos"][1]

        if (disc.get("speed") != None):
            self.xspeed = disc["speed"][0]
            self.yspeed = disc["speed"][1]

        if (disc.get("cGroup") != None):
            self.cGroup = disc["cGroup"]

        if (disc.get("cMask") != None):
            self.cMask = disc["cMask"]

        if (disc.get("trait") != None):
            self.trait = disc["trait"]

    def setDiscDefaultProperties(self, defaultDisc):
        self.x = defaultDisc.x
        self.y = defaultDisc.y
        self.xspeed = defaultDisc.xspeed
        self.yspeed = defaultDisc.yspeed
        self.radius = defaultDisc.radius
        self.bCoef = defaultDisc.bCoef
        self.invMass = defaultDisc.invMass
        self.damping = defaultDisc.damping
        self.cGroup = defaultDisc.cGroup
        self.cMask = defaultDisc.cMask


class ballPhysics(Disc):
	def __init__(self):
		super().__init__(haxVal['playerPhysics'])


class playerPhysics(Disc):
    def __init__(self):
        super().__init__(haxVal['playerPhysics'])
        self.acceleration = 0.1
        self.kickingAcceleration = 0.07
        self.kickingDamping = 0.96
        self.kickStrength = 5


class Game:
    def __init__(self, stadiumUsed = None, stadiumStored = None):
        self.state = 0
        self.start = True
        self.timeout = 0
        self.timeLimit = 3
        self.scoreLimit = 3
        self.kickoffReset = 8
        self.red = 0
        self.blue = 0
        self.time = 0
        self.teamGoal = haxVal['Team']["SPECTATORS"]
        self.players = []
        self.stadiumUsed = stadiumUsed
        self.stadiumStored = stadiumStored
        self.rec = []
        self.currentFrame = -1
        self.observation_space = self.get_obs_space()

    def addPlayer(self, player):
        player.setPlayerDefaultProperties(self.stadiumUsed)
        self.players.append(player)

    def step(self):
        self.currentFrame += 1
        scoreIndex = 0
        scorableDiscsId = [0 for i in range(256)]
        scorableDiscsPos = [[0, 0] for i in range(256)]
        discs = self.stadiumUsed['discs']
        planes = self.stadiumUsed['planes']
        segments = self.stadiumUsed['segments']
        vertexes = self.stadiumUsed['vertexes']

        for i in range(len(discs)):
            disc = discs[i]
            if ((disc.cGroup & 128) != 0):
                scorableDiscsId[scoreIndex] = i
                scorableDiscsPos[scoreIndex][0] = disc.x
                scorableDiscsPos[scoreIndex][1] = disc.y
                scoreIndex += 1

        for i in range(len(self.players)):
            p = self.players[i]
            if p.team["id"] != 0:
                if p.bot:
                    p.bot(p, {'currentFrame': self.currentFrame,
                              'discs': self.stadiumUsed['discs']})
                fnHax.resolvePlayerMovement(p, discs)
                self.rec[i][1].append(p.inputs)

        for d in discs:
            d.x += d.xspeed
            d.y += d.yspeed
            d.xspeed *= d.damping
            d.yspeed *= d.damping

        for i in range(len(discs)):
            d_a = discs[i]
            for j in range(i + 1, len(discs)):
                d_b = discs[j]
                if (((d_a.cGroup & d_b.cMask) != 0) and ((d_a.cMask & d_b.cGroup) != 0)):
                    fnHax.resolveDDCollision(d_a, d_b)
            if (d_a.invMass != 0):
                for p in planes:
                    if (((d_a.cGroup & p.cMask) != 0) and ((d_a.cMask & p.cGroup) != 0)):
                        fnHax.resolveDPCollision(d_a, p)
                for s in segments:
                    if (((d_a.cGroup & s.cMask) != 0) and ((d_a.cMask & s.cGroup) != 0)):
                        fnHax.resolveDSCollision(d_a, s)
                for v in vertexes:
                    if (((d_a.cGroup & v.cMask) != 0) and ((d_a.cMask & v.cGroup) != 0)):
                        fnHax.resolveDVCollision(d_a, v)

        if (self.state == 0):  # "kickOffReset"
            for disc in discs:
                if disc.x != None:
                    disc.cMask = 39 | self.kickoffReset
            ball = discs[0]
            if (ball.xspeed * ball.xspeed + ball.yspeed * ball.yspeed > 0):
                self.state = 1

        elif (self.state == 1):  # "gameInGoing"
            self.time += 0.016666666666666666
            for disc in discs:
                if disc.x != None:
                    disc.cMask = 39
            scoreTeam = haxVal['Team']["SPECTATORS"]
            for i in range(scoreIndex):
                scoreTeam = fnHax.checkGoal(
                    [discs[scorableDiscsId[i]].x, discs[scorableDiscsId[i]].y], scorableDiscsPos[i], self.stadiumUsed)
                if (scoreTeam != haxVal['Team']["SPECTATORS"]):
                    break
            if (scoreTeam != haxVal['Team']["SPECTATORS"]):
                self.state = 2
                self.timeout = 150
                self.teamGoal = scoreTeam
                self.kickoffReset = scoreTeam["id"] * 8
                if scoreTeam["id"] == haxVal['Team']["BLUE"]["id"]:
                    self.red += 1
                else:
                    self.blue += 1
            else:
                if (self.timeLimit > 0 and self.time >= 60 * self.timeLimit and self.red != self.blue):
                    self.endAnimation()

        elif (self.state == 2):  # "goalScored"
            self.timeout -= 1
            if (self.timeout <= 0):
                if ((self.scoreLimit > 0 and (self.red >= self.scoreLimit or self.blue >= self.scoreLimit)) or self.timeLimit > 0 and self.time >= 60 * self.timeLimit and self.red != self.blue):
                    self.endAnimation()
                else:
                    self.resetPositionDiscs()

        elif (self.state == 3):  # "gameEnding"
            self.timeout -= 1
            if (self.timeout <= 0 and self.start):
                self.start = False
                return True

        return False
    
    def resetPositionDiscs(self):
        self.state = 0
        self.stadiumUsed['discs'][0].setDiscDefaultProperties(
            self.stadiumStored['discs'][0])
        teamArray = [0, 0, 0]
        for i in range(len(self.players)):
            player = self.players[i]
            player.setPlayerDefaultProperties(self.stadiumUsed)
            teamP = player.team
            if (teamP != haxVal['Team']["SPECTATORS"]):
                valueArr = teamArray[teamP['id']]
                fact = valueArr + 1 >> 1
                if ((valueArr % 2) == 1):
                    fact = -fact
                pos_x = self.stadiumStored['spawnDistance'] * (2 * teamP['id'] - 3)
                pos_y = 55 * fact
                player.disc.x = pos_x
                player.disc.y = pos_y
                teamArray[teamP['id']] += 1

    def endAnimation(self):
        self.state = 3
        self.timeout = 300

    def start_game(self):
        self.rec = [[[p.name, p.avatar, p.team["id"]], []] for p in self.players]
        self.resetPositionDiscs()

    def play_game(self):
        done = False
        while done == False:
            done = self.step()

    def reset_game(self):
        playerStore = [[p.name, p.avatar, p.team, p.controls, p.bot] for p in self.players]
        self = Game(self.stadiumStored, self.stadiumStored)
        for arr in playerStore:
            self.addPlayer(Player(arr[0], arr[1], arr[2], arr[3], arr[4]))

    def saveRecording(self, fileName):
        with open(fileName, 'w+') as f:
            json_rec = json.dumps(self.rec, separators=(',', ':'))
            f.write(json_rec)

    def get_stadium_obs_space(self):
        generalList = [self.stadiumUsed['height'], self.stadiumUsed['spawnDistance'], self.stadiumUsed['height']]
        discList = [[np.nan for i in range(fnHax.getSizeProp(utilsHax.discProperties))] for j in range(256)]
        vertexList = [[np.nan for i in range(fnHax.getSizeProp(utilsHax.vertexProperties))] for j in range(256)]
        segmentList = [[np.nan for i in range(fnHax.getSizeProp(utilsHax.segmentProperties))] for j in range(256)]
        planeList = [[np.nan for i in range(fnHax.getSizeProp(utilsHax.planeProperties))] for j in range(256)]
        goalList = [[np.nan for i in range(fnHax.getSizeProp(utilsHax.goalProperties))] for j in range(256)]

        discs = self.stadiumUsed['discs']
        planes = self.stadiumUsed['planes']
        segments = self.stadiumUsed['segments']
        vertexes = self.stadiumUsed['vertexes']
        goals = self.stadiumUsed['goals']

        for i in range(len(discs)):
            discList[i] = list(np.hstack(fnHax.transformObjectToList(discs[i], utilsHax.discProperties)))
        for i in range(len(vertexes)):
            vertexList[i] = list(np.hstack(fnHax.transformObjectToList(vertexes[i], utilsHax.vertexProperties)))
        for i in range(len(segments)):
            segmentList[i] = list(np.hstack(fnHax.transformObjectToList(segments[i], utilsHax.segmentProperties)))
        for i in range(len(planes)):
            planeList[i] = list(np.hstack(fnHax.transformObjectToList(planes[i], utilsHax.planeProperties)))
        for i in range(len(goals)):
            goalList[i] = list(np.hstack(fnHax.transformObjectToList(goals[i], utilsHax.goalProperties)))
        return list(np.hstack(generalList + discList + vertexList + segmentList + planeList + goalList))

    def get_game_obs_space(self):
        return [self.blue, self.kickoffReset, self.red, self.scoreLimit, self.state, self.time, self.timeLimit]

    def get_obs_space(self):
        return list(np.hstack(self.get_game_obs_space() + self.get_stadium_obs_space()))

    def update_obs_space(self):
        discList = [[np.nan for i in range(fnHax.getSizeProp(utilsHax.discProperties))] for j in range(256)]
        discs = self.stadiumUsed['discs']
        for i in range(len(discs)):
            discList[i] = list(np.hstack(fnHax.transformObjectToList(discs[i], utilsHax.discProperties)))
        self.observation_space = list(np.hstack(self.get_game_obs_space() + discList)) + self.observation_space[3591:]


class Player:
    def __init__(self, name=None, avatar=None, team=None, controls=None, bot=None):
        if (name != None):
            self.name = name
        else:
            self.name = "Player"

        if (team != None):
             self.team = team
        else:
            self.team = haxVal['Team']["SPECTATORS"]

        if (avatar != None):
            self.avatar = avatar
        else:
            self.avatar = ''

        if (controls != None):
             self.controls = controls
        else:
            self.controls = [["ArrowUp"], ["ArrowLeft"],
                             ["ArrowDown"], ["ArrowRight"], ["KeyX"]]

        self.bot = bot

        self.disc = None
        self.inputs = 0
        self.shooting = False
        self.shotReset = False
        self.spawnPoint = 0

    def setPlayerDefaultProperties(self, stadium):
        if (self.team == haxVal["Team"]["SPECTATORS"]):
            self.disc = None
        else:
            self.inputs = 0
            if (self.disc == None):
                b = playerPhysics()
                self.disc = b
                stadium['discs'].append(b)

            c = fnHax.collisionTransformation(Disc(haxVal['playerPhysics']))
            self.disc.radius = c.radius
            self.disc.invMass = c.invMass
            self.disc.damping = c.damping
            self.disc.bCoef = c.bCoef
            if (self.team == haxVal['Team']["RED"]):
                self.disc.cMask = 39 + haxVal['collisionFlags']["redKO"]
            else:
                self.disc.cMask = 39 + haxVal['collisionFlags']["blueKO"]
            self.disc.cGroup = self.team["cGroup"] | c.cGroup
            self.disc.x = (2 * self.team["id"] - 3) * stadium["width"]
            self.disc.y = 0
            self.disc.xspeed = 0
            self.disc.yspeed = 0

    def checkKick(self):
        if (self.shotReset):
            return not(self.shooting)
        return self.shooting


class Vertex:
    def __init__(self, vertex):
        self.x = vertex["x"]
        self.y = vertex["y"]

        if (vertex.get("trait") != None):
            self.trait = vertex["trait"]

        if (vertex.get("bCoef") != None):
            self.bCoef = vertex["bCoef"]

        if (vertex.get("cMask") != None):
            self.cMask = vertex["cMask"]

        if (vertex.get("cGroup") != None):
            self.cGroup = vertex["cGroup"]


class Segment:
    def __init__(self, segment):
        self.v0 = segment['v0']
        self.v1 = segment['v1']

        if (segment.get("trait") != None):
            self.trait = segment["trait"]

        if (segment.get("bCoef") != None):
            self.bCoef = segment["bCoef"]

        if (segment.get("cMask") != None):
            self.cMask = segment["cMask"]

        if (segment.get("cGroup") != None):
            self.cGroup = segment["cGroup"]

        if (segment.get("curve") != None):
            self.curve = segment["curve"]

    def getStuffSegment(self):
        if (hasattr(self, "curveF")):
            segV1 = {"x": self.v1[0], "y": self.v1[1]}
            segV0 = {"x": self.v0[0], "y": self.v0[1]}
            dist_x = 0.5 * (segV1["x"] - segV0["x"])
            dist_y = 0.5 * (segV1["y"] - segV0["y"])
            self.circleCenter = [segV0["x"] + dist_x - dist_y * self.curveF,
                                 segV0["y"] + dist_y + dist_x * self.curveF]
            dist_x_CC = segV0["x"] - self.circleCenter[0]
            dist_y_CC = segV0["y"] - self.circleCenter[1]
            self.circleRadius = math.sqrt(
                dist_x_CC * dist_x_CC + dist_y_CC * dist_y_CC)
            self.v0Tan = [-(segV0["y"] - self.circleCenter[1]),
                          segV0["x"] - self.circleCenter[0]]
            self.v1Tan = [-(self.circleCenter[1] - segV1["y"]),
                            self.circleCenter[0] - segV1["x"]]
            if (self.curveF <= 0):
                self.v0Tan[0] *= -1
                self.v0Tan[1] *= -1
                self.v1Tan[0] *= -1
                self.v1Tan[1] *= -1
        else:
            segV0 = {"x": self.v0[0], "y": self.v0[1]}
            segV1 = {"x": self.v1[0], "y": self.v1[1]}
            dist_x = segV0["x"] - segV1["x"]
            dist_y = -(segV0["y"] - segV1["y"])
            dist = math.sqrt(dist_x * dist_x + dist_y * dist_y)
            setattr(self, 'normal', [dist_y / dist, dist_x / dist])

    def getCurveFSegment(self):
        a = self.curve
        a *= .017453292519943295
        if (a < 0):
            a *= -1
            self.curve *= -1
            b = self.v0
            self.v0 = self.v1
            self.v1 = b

        liminf = 0.17435839227423353
        limsup = 5.934119456780721
        if (a > liminf and a < limsup):
            self.curveF = 1 / math.tan(a / 2)


class Plane:
    def __init__(self, plane):
        self.normal = plane["normal"]
        self.dist = plane["dist"]

        if (plane.get("trait") != None):
            self.trait = plane["trait"]

        if (plane.get("bCoef") != None):
            self.bCoef = plane["bCoef"]

        if (plane.get("cMask") != None):
            self.cMask = plane["cMask"]

        if (plane.get("cGroup") != None):
            self.cGroup = plane["cGroup"]


class Goal:
    def __init__(self, goal):
        self.p0 = goal["p0"]
        self.p1 = goal["p1"]
        self.team = goal["team"]

        if (goal.get("trait") != None):
            self.trait = goal["trait"]
