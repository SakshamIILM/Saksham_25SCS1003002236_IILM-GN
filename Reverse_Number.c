#include <stdio.h>

// Function to reverse a number
int reverseNumber(int num) {
    int reversed = 0;
    while (num != 0) {
        int digit = num % 10;
        reversed = reversed * 10 + digit;
        num /= 10;
    }
    return reversed;
}

int main() {
    int number;

    printf("Enter a number: ");
    scanf("%d", &number);

    int result = reverseNumber(number);
    printf("The reverse of %d is %d\n", number, result);

    return 0;
}