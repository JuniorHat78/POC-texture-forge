//snake game
var canvas = document.getElementById("canvas");
var context = canvas.getContext("2d");
//context.rect(0,0,50,50);
//context.fillStyle = "red";
//context.fill();
for (let i = 0; i<= 12; i++){
    for (let j = 0; j<= 8; j++){
        if ((i+j)%2 == 0){
            context.beginPath();
            context.rect(i*50,j*50,50,50);
            context.fillStyle = "lime";
            context.fill();
        }
    }
}