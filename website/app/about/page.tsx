export const metadata = { title: "About — HappyCake US" };

export default function About() {
  return (
    <div className="prose prose-stone max-w-3xl">
      <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">About</p>
      <h1 className="font-display text-4xl text-happy-blue-900 mt-2">It started with a phrase.</h1>
      <p className="text-lg italic text-happy-blue-700">"It's just like homemade."</p>
      <p>
        We started baking cakes — as if for ourselves. Delicious, sweet, fresh cakes. People kept
        coming back saying <em>"it tastes like I baked it myself"</em> and{" "}
        <em>"it tastes so good — like real home baking"</em>. We realised that was the centre of
        what we wanted to make.
      </p>
      <p>
        Every ingredient is carefully selected. Every cake is hand-decorated and hand-packed.
        Every recipe was perfected over years until it earned its name.
      </p>
      <p>
        When customers choose our cakes for the moments that matter — birthdays, anniversaries,
        the quiet week-night dinner — our hearts cheer and sink at once. That mix of pride and
        responsibility is what keeps us improving every day.
      </p>
      <p className="font-display text-xl text-happy-blue-900 mt-8">
        We love watching people be happy. We love making delicious things. The combination is
        HappyCake.
      </p>
    </div>
  );
}
