colors = ['G', 'R', 'B', 'Y']
numbers = [str(i) for i in range(10)]

result = [f"{num}_{color}" for color in colors for num in numbers]
result += result
print(result)
