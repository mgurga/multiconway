var c = document.getElementsByTagName('canvas')[0];
var ctx = c.getContext('2d');
var deviceWidth = window.innerWidth;
var deviceHeight = window.innerHeight;
var nativeWidth = 1600;
var nativeHeight = 900;
var scaleFillNative = Math.max(deviceWidth / nativeWidth, deviceHeight / nativeHeight);
c.width = deviceWidth;
c.height = deviceHeight;

var serverupdateint;
var squaresize = 40
var boardsize = 401
var scrollx = 0
var scrolly = 0
var usercolor = [Math.floor(rand(150, 255)), Math.floor(rand(150, 255)), Math.floor(rand(150, 255))]
var dragging = false
var dragstart = [0, 0]
var dragpos = [0, 0]
var mousepos = [0, 0]
var realscroll = [0, 0]
var cells = []
var lastupdate = Date.now()
var showui = true
var getcellint

fetch('/info').then(response => response.json()).then(data => { 
    serverupdateint = data.update
    getcellint = setInterval(() => { getCells() }, (serverupdateint / 2) * 1000)
})

function draw() {
    drawGrid()
    drawCells()
    if (showui)
        drawUI()
    if (dragging) {
        scrollx += mousepos[0] - dragpos[0]
        scrolly += mousepos[1] - dragpos[1]
        realscroll[0] += mousepos[0] - dragpos[0]
        realscroll[1] += mousepos[1] - dragpos[1]
        dragpos[0] = mousepos[0]
        dragpos[1] = mousepos[1]
    }
    requestAnimationFrame(draw);
}

function drawUI() {
    ctx.fillStyle = "rgba(255, 255, 255, .3)"
    ctx.fillRect(20, 20, 300, 90)

    if (Date.now() - lastupdate < 200) {
        ctx.fillStyle = "rgb(100, 255, 100)"
    } else {
        ctx.fillStyle = "rgb(255, 255, 255)"
    }
    ctx.font = ctx.font.replace(/\d+px/, "20px");
    if (serverupdateint != undefined) {
        ctx.fillText("server update interval: " + serverupdateint + " sec", 22, 40)
    }
    ctx.fillStyle = "rgb(255, 255, 255)"
    ctx.fillText("click: to place cell", 22, 60)
    ctx.fillText("click + drag: move point of view", 22, 80)
    ctx.fillText("press H to toggle this message", 22, 100)
}

function drawCells() {
    for (const c of cells) {
        ctx.fillStyle = "rgb(" + c.r + "," + c.g + "," + c.b + ")"
        ctx.fillRect((c.x * squaresize) + realscroll[0], (c.y * squaresize) + realscroll[1], squaresize, squaresize)
    }
}

function drawGrid() {
    ctx.fillStyle = "#000000"
    ctx.fillRect(0, 0, c.width, c.height)
    ctx.strokeStyle = "#111111"

    for (var x = -boardsize; x < boardsize; x++) {
        for (var y = -boardsize; y < boardsize; y++) {
            if (x * squaresize + scrollx < c.width && x * squaresize + scrollx > -squaresize) { // check x if rendered
                if (y * squaresize + scrolly < c.height && y * squaresize + scrolly > -squaresize) { // check y if rendered
                    ctx.strokeRect((x * squaresize) + scrollx, (y * squaresize) + scrolly, squaresize, squaresize)
                }
            }
        }
    }

    if (scrollx > squaresize) { scrollx = scrollx - squaresize }
    if (scrolly > squaresize) { scrolly = scrolly - squaresize }
    if (scrollx < -squaresize) { scrollx = scrollx + squaresize }
    if (scrolly < -squaresize) { scrolly = scrolly + squaresize }
}

function getCells() {
    fetch("/api/getcells")
    .then(res => res.json())
    .then(data => {
        lastupdate = Date.now()
        cells = []
        for (var c in data) {
            cells.push(data[c])
        }
    })
}

function mouseClick(e) {
    var blockx = Math.floor((e.clientX - realscroll[0]) / squaresize)
    var blocky = Math.floor((e.clientY - realscroll[1]) / squaresize)
    console.log("clicked x: " + blockx + " y: " + blocky);
    addCell(blockx, blocky)
}

function addCell(x, y) {
    var data = {"x": x, "y": y, "r": usercolor[0], "g": usercolor[1], "b": usercolor[2]}
    fetch("/api/addcell", {
        method: "POST",
        headers: {'Content-Type': 'application/json'}, 
        body: JSON.stringify(data)
    }).then(res => {
        getCells()
    });
}

function rand(min, max) { return Math.random() * (max - min) + min; }
c.addEventListener("mousedown", (e) => {
    dragging = true
    dragpos[0] = dragstart[0] = e.clientX
    dragpos[1] = dragstart[1] = e.clientY
})
c.addEventListener("mousemove", (e) => {
    [mousepos[0], mousepos[1]] = [e.clientX, e.clientY]
})
c.addEventListener("mouseup", (e) => {
    dragging = false
    if (dragstart[0] == mousepos[0] && dragstart[1] == mousepos[1]) { mouseClick(e) }
})

draw()
getCells() 
document.addEventListener("keypress", event => {
    if (event.key == "h")
        showui = !showui
})