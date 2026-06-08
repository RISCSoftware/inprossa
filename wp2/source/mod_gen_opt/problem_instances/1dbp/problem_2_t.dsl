A : DSList(4, DSInt()) = [5, 5, 5, 5]
B : DSList(5, DSInt()) = [3, 2, 5, 3, 1]

NA : int = 5
NB : int = 5

variables: DSList(NB, DSInt(1, NA)) 


def not_exceed(variables: DSList(NB, DSInt(1, NA))):
    c: DSList(NA, DSInt(1, sum(B))) 
    #= [1] * (NA)
    objective = 0
    for i in range(1, NA):
        c[i] = 0
        for j in range(1, NB):
            if variables[j] == i:
                c[i] = c[i] + B[j]

        assert c[i] <= A[i]
        if c[i] > 0:
            objective = objective + 1
    return objective

