const number1 = document.getElementById('number1');
const operator = document.getElementById('operator');
const number2 = document.getElementById('number2');
const equals = document.getElementById('equals');

const num1 = document.getElementById('num-1');
const num2 = document.getElementById('num-2');
const num3 = document.getElementById('num-3');
const operatorDivision = document.getElementById('operator-/');

const num4 = document.getElementById('num-4');
const num5 = document.getElementById('num-5');
const num6 = document.getElementById('num-6');
const operatorMultiplication = document.getElementById('operator-*');

const num7 = document.getElementById('num-7');
const num8 = document.getElementById('num-8');
const num9 = document.getElementById('num-9');
const operatorSubtraction = document.getElementById('operator--');

const  num0 = document.getElementById('num-0');
const operatorClear = document.getElementById('operator-clear');
const operatorEqual = document.getElementById('operator-equals');
const operatorAddition = document.getElementById('operator-+');

let arrNumbers = [num1, num2, num3, num4, num5, num6, num7, num8, num9, num0];
let arrOperators = [operatorDivision, operatorMultiplication, operatorSubtraction, operatorAddition];


function clearDisplay() {
    console.log('Clearing display...');
    number1.value = '';
    operator.value = '';
    number2.value = '';
    equals.value = '= ';
}

function calculate() {
    console.log('Calculating result...');
    let num1Value = parseFloat(number1.value);
    let num2Value = parseFloat(number2.value);
    let result;

    if (isNaN(num1Value) || isNaN(num2Value)) {
        alert('Please enter valid numbers.');
        return;
    }

    switch (operator.value) {
        case '+':
            result = num1Value + num2Value;
            break;
        case '-':
            result = num1Value - num2Value;
            break;
        case '*':
            result = num1Value * num2Value;
            break;
        case '/':
            if (num2Value === 0) {
                result = "no"
                return;
            }
            result = num1Value / num2Value;
            break;
        default:
            alert('Please select a valid operator.');
            return;
    }
    console.log('Calculating result...', num1Value, num2Value, result);
    equals.value += result
}


for (let btn of arrNumbers) {
    console.log(btn);
    btn.addEventListener('click', function () {
        console.log('Num button clicked:', btn.textContent);
        if (operator.value === '') {
            number1.value += btn.textContent;
        } else {
            number2.value += btn.textContent;
        }
    });
}

for (let btn of arrOperators) {
    console.log(btn);
    btn.addEventListener('click', function () {
        console.log('Operator button clicked:', btn.textContent);
        operator.value = btn.textContent;
    });
}

operatorEqual.addEventListener('click', function() {
    equals.value = '= ';
    calculate()
});

operatorClear.addEventListener('click', function() {
    clearDisplay();
});

console.log('Calculator script loaded successfully.');