from flask import Flask, send_from_directory, request
from apscheduler.schedulers.background import BackgroundScheduler
import os
from copy import copy
from datetime import datetime
import logging
import shelve

UPDATE_INTERVAL = 5
BOUNDS = 5000

logging.getLogger("werkzeug").disabled = True
app = Flask("multiconways")
app.logger.setLevel(logging.INFO)
public = os.path.join(os.path.dirname(__file__), "public")

class Cell:
    def __init__(self, x: int, y: int, r: int, g: int, b: int, alive: bool = True) -> None:
        (self.x, self.y, self.r, self.g, self.b, self.alive) = x, y, r, g, b, alive
    def __str__(self) -> str:
        return f"x: {self.x} y: {self.y} alive: {self.alive}"
    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "r": self.r, "g": self.g, "b": self.b}
cells = set()

if not os.path.isfile("cells"):
    app.logger.info("no backup file detected, creating one")
    with shelve.open("cells") as f:
        f["cells"] = set()

try:
    with shelve.open("cells") as f:
        cells = set(f["cells"])
        app.logger.info(f"loaded {len(cells)} cells from backup")
except Exception as e:
    app.logger.warning("failed to load backup (you should probably delete the 'cells' file)")

def save_cells():
    global cells
    app.logger.info("saved cells")
    with shelve.open("cells") as f:
        f["cells"] = cells

@app.route("/")
def index(): return send_from_directory(public, "index.html")
@app.route("/play")
def play(): return send_from_directory(public, "play.html")
@app.route("/game.js")
def js(): return send_from_directory(public, "game.js")
@app.route("/info")
def info(): return {"update": UPDATE_INTERVAL, "totalcells": len(cells)}

@app.route("/api/addcell", methods=["POST"])
def add_cell():
    req = request.get_json()
    if req != None:
        app.logger.info(f"adding cell at x: {req['x']}, y: {req['y']}")
        nc = Cell(req['x'], req['y'], req['r'], req['g'], req['b'], True)
        if not (nc.x >= BOUNDS or nc.y >= BOUNDS or nc.x <= -BOUNDS or nc.y <= -BOUNDS):
            for c in cells:
                if c.x == nc.x and c.y == nc.y:
                    cells.remove(c)
                    break
            cells.add(nc)
            add_dead_cells_around(Cell(req['x'], req['y'], req['r'], req['g'], req['b']))
        else:
            app.logger.info("not adding cell, out of bounds")
        return "OK", 200
    else:
        return "ERROR", 404

@app.route("/api/getcells")
def get_cells():
    out: dict = {}
    clist = list(cells)
    for i in range(0, len(clist)):
        if clist[i].alive:
            out.update({i: clist[i].to_dict()})
    return out

def step():
    stepstart = datetime.now()
    global cells
    newcells: set[Cell] = set()
    newcpos: list[Cell] = []

    if (len(cells) == 0):
        return

    for c in cells:
        adj = neighbors(c)
        newc = copy(c)

        # Kill cell if out of bounds
        if c.x >= BOUNDS or c.y >= BOUNDS or c.x <= -BOUNDS or c.y <= -BOUNDS:
            newc.alive = False

        # 1. Any live cell with fewer than two live neighbours dies, as if by underpopulation.
        if adj == 1 or adj == 0 and c.alive:
            newc.alive = False
            newcells.add(newc)

        # 2. Any live cell with two or three live neighbours lives on to the next generation.
        if (adj == 2 or adj == 3) and c.alive:
            newcells.add(newc)

        # 3. Any live cell with more than three live neighbours dies, as if by overpopulation.
        if adj > 3 and c.alive:
            newc.alive = False
            newcells.add(newc)

        # 4. Any dead cell with exactly three live neighbours becomes a live cell, as if by reproduction.
        if adj == 3 and c.alive == False:
            newc.alive = True
            newcells.add(newc)
            newcpos.append(newc)
        
        # carry over dead cells
        if c.alive == False:
            newcells.add(newc)

    cells = newcells
    for new_cell in newcpos:
        add_dead_cells_around(new_cell)

    app.logger.info(f"step finished, took {datetime.now() - stepstart}. {len(cells)} total cells")
    save_cells()

def add_dead_cells_around(c: Cell):
    for i in range(-1, 2):
        if not cell_at(c.x + i, c.y + 1):
            cells.add(Cell(c.x + i, c.y + 1, c.r, c.g, c.b, False))
        if not cell_at(c.x + i, c.y - 1):
            cells.add(Cell(c.x + i, c.y - 1, c.r, c.g, c.b, False))

    if not cell_at(c.x + 1, c.y):
        cells.add(Cell(c.x + 1, c.y, c.r, c.g, c.b, False))
    if not cell_at(c.x - 1, c.y):
        cells.add(Cell(c.x - 1, c.y, c.r, c.g, c.b, False))

def neighbors(cell: Cell) -> int:
    out = 0
    for c in cells:
        if c.alive:
            if cell.x == c.x + 1 and cell.y == c.y - 1: # upper left
                out = out + 1
            if cell.x == c.x and cell.y == c.y - 1: # upper middle
                out = out + 1
            if cell.x == c.x - 1 and cell.y == c.y - 1: # upper right
                out = out + 1
            if cell.x == c.x + 1 and cell.y == c.y: # middle left
                out = out + 1
            if cell.x == c.x - 1 and cell.y == c.y: # middle right
                out = out + 1
            if cell.x == c.x + 1 and cell.y == c.y + 1: # lower left
                out = out + 1
            if cell.x == c.x and cell.y == c.y + 1: # lower middle
                out = out + 1
            if cell.x == c.x - 1 and cell.y == c.y + 1: # lower right
                out = out + 1
    return out

def cell_at(x: int, y: int) -> bool:
    for c in cells:
        if c.x == x and c.y == y:
            return True
    return False

sched = BackgroundScheduler(daemon=True)
sched.add_job(step, 'interval', seconds=UPDATE_INTERVAL)
sched.start()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=False)