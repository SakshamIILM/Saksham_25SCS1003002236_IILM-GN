#include <stdio.h>
#include <math.h>

// Function to check if a number is an Armstrong number
int isArmstrong(int num) {
    int originalNum = num, remainder, n = 0;
    double result = 0.0;

    // Count number of digits
    while (originalNum != 0) {
        originalNum /= 10;
        n++;
    }

    originalNum = num;

    // Calculate the sum of the nth power of digits
    while (originalNum != 0) {
        remainder = originalNum % 10;
        result += pow(remainder, n);
        originalNum /= 10;
    }

    // Return 1 if Armstrong, else 0
    return (int)result == num;
}

int main() {
    printf("Armstrong numbers from 1 to 1000 are:\n");

    for (int i = 1; i <= 1000; i++) {
        if (isArmstrong(i))
            printf("%d ", i);
    }

    printf("\n");
    return 0;
}