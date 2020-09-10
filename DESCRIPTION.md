# Ro Engineering Take-Home Exercise

Hello! We’re excited that you’re interested in coming to work with us. Below
you’ll find an exercise that will help us get acquainted with your skills and
strengths. We expect this to take between two to three hours to complete (if
you find you’re spending more time on it, send us a note).

Feel free to use any major programming language you’d like (Javascript, Go,
PHP, Ruby, Python, Java, Scala, Kotlin are all great choices), as well as any
libraries that you feel would be helpful. We only ask that you submit code that
you would be comfortable shipping and maintaining in production. And of course,
only submit your own original work.

When you’re done, please create a README describing how we can run your code,
and email your recruiter a zip file containing your solution.

If you have questions, please feel free to contact your recruiter. We’re more
than happy to help clarify or address any concerns you may have.

## Context

Ro’s platform enables physicians to diagnose patients and prescribe medications
for many common conditions. When prescribing medications, our physicians are
constantly looking for a risk known as a drug interaction, which occurs when a
patient's response to a drug is affected by factors such as food, supplements,
environmental factors, other drugs or disease.

At Ro, we dedicate ourselves to ensuring the safety of our patients. Before
prescribing any medication, we ask patients to tell us any other drugs they’re
currently taking, which allows our physicians to find any potential risks the
patient may face by introducing a new medication.

## Problem

Given an `interactions.json` file containing a list of drug-drug interactions,
write a command line program that accepts a space-separated list of drugs per
line and determines if there is a risk of interaction between any drugs in the
list.

If there are multiple interactions detected for a single line of input, the
program should return the most severe interaction. If there are multiple
interactions of the same severity, your solution should return the interaction
that appears first in the `interactions.json` file.

The program should read its input from STDIN and write its output to STDOUT,
where each line of input should generate a line of output in the same order.

## Examples

_Note: all examples are based on the `interactions.json` file included with
this description._

### Input (each line represents one line of input)

```
sildenafil tamsulosin valaciclovir
sildenafil ibuprofen
valaciclovir doxepin ticlopidine ibuprofen
```

### Output (order should match the input above)

```
MODERATE: Sildenafil may potentiate the hypotensive effect of alpha blockers, resulting in symptomatic hypotension in some patients.
No interaction
MAJOR: Valaciclovir may decrease the excretion rate of Doxepin which could result in a higher serum level.
```

## Constraints

- Number of medications per line between 1 and 20
- Number of lines per execution between 1 and 10,000
