# What is this, in plain words?

## The problem

Hospitals record huge amounts of information about patients — who got which
treatment, who got better, who didn't. It is tempting to mine those records to
answer questions like *"does giving this drug early help people survive?"*

The catch: medical records are **not experiments**. The sickest patients tend to
get the most aggressive treatments. So if you just compare "people who got the
drug" to "people who didn't," the drug can look harmful even when it helps —
simply because the people who got it were sicker to begin with. This trap is
called *confounding*, and naive analyses fall into it constantly. A wrong answer
here doesn't stay on a screen; it can change how a real patient is treated.

## What we built

An **evidence engine**: a careful, automated pipeline that tries to answer those
"does X affect Y?" questions from hospital records *while refusing to fool itself
or anyone else*. Its defining feature is humility. The strongest thing it is even
*allowed* to say is **"this is a hypothesis worth testing in a proper trial."** It
can never say "do this." Saying anything stronger isn't discouraged — it's made
impossible in the code.

## How it avoids fooling itself

Think of it as a checklist that a very disciplined, very paranoid researcher would
follow — except the discipline is enforced by the software, not by willpower:

1. **Commit the question in advance.** It writes down exactly what it's asking
   *before* it's allowed to look at who lived or died — so it can't quietly change
   the question to match a result it likes.
2. **Check the data for known biases first.** For example, pulse-oximeters (the
   finger clip that measures oxygen) are known to read falsely high on patients
   with darker skin. The engine looks for problems like this *before* doing
   anything else, and carries the warnings through to the end.
3. **Make humans approve the assumptions.** Deciding "which factors matter" is the
   step that secretly determines the answer. The engine refuses to run until people
   — including a clinician *and* someone from an affected patient community — have
   signed off on those assumptions. The computer is not allowed to declare truth
   on its own.
4. **Answer the question five different ways.** It uses five separate statistical
   methods that fail for different reasons, and only trusts a finding if they all
   agree. One method agreeing with itself proves nothing; five different ones
   agreeing is hard to dismiss.
5. **Use a "ruler" to catch leftover bias.** It also measures things the treatment
   *cannot possibly* affect. If it "finds an effect" on those, it knows there's
   residual bias — and it measures and subtracts that bias from the real answer.
6. **Keep an unforgeable record.** Every step is chained together with a digital
   fingerprint, so anyone can independently verify the result was produced honestly
   and re-run it to get the exact same numbers. You don't have to *trust* it; you
   can *check* it.
7. **Say where the evidence is missing.** It reports results separately for
   different groups and openly flags when there's enough data for one group but not
   another — instead of hiding a blind spot behind an average.

## How do we know it actually works?

We tested it on **made-up data where we secretly know the true answer**, thousands
of times over. A correct engine should: recover the true effect, *not* cry wolf
when there's no effect, and be honest about its own uncertainty.

That's exactly what happened. The naive approach was badly wrong (it "found"
effects that weren't there every single time). Our engine matched the hidden truth
almost exactly, raised a false alarm only about 5% of the time (the textbook
target), and its stated confidence was truthful. When we secretly added a hidden
bias, its self-correction step cleaned most of it back out.

## The bottom line

It's a machine for turning messy, real-world medical records into **honest,
clearly-labelled hypotheses** — engineered so that, when it isn't sure, it would
rather say *"I don't know"* than mislead a doctor. It doesn't replace clinical
trials or human judgment; it points to the questions most worth asking, and shows
its work so others can check it.
