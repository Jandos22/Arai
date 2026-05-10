# Food-truck weekly route — marketing-agent draft

> Generated 2026-05-10T08:00:00Z by `orchestrator.food_truck_route`
> from `orchestrator/fixtures/food_truck_customers.json`. All numbers
> below are deterministic from the fixture + clustering seed; nothing
> is invented. Owner approves via Telegram before the truck rolls.

## Summary

- Stops: **5** (one weekday afternoon each, 3:00 PM – 7:00 PM)
- Customers covered: **25**
- Baseline orders/month (single-store today): **23.2**
- Projected orders/month with truck: **42.93**
- Incremental orders/month: **19.73**
- Incremental revenue/month: **$892.25**

Lift factor: **×1.85** for customers within 5 miles of the stop centroid. Outliers stay at baseline.

## Stops

| Day | Anchor | Customers | Hero | Δ orders/mo | Δ revenue/mo |
|---|---|---:|---|---:|---:|
| Mon | Telfair | 9 | cake "Honey" | 7.40 | $278.20 |
| Tue | Silverlake | 5 | cake "Honey" | 2.89 | $119.09 |
| Wed | Stafford | 5 | cake "Napoleon" | 4.50 | $283.05 |
| Thu | Sienna | 4 | cake "Honey" | 3.32 | $140.08 |
| Fri | Aliana | 2 | cake "Milk Maiden" | 1.62 | $71.83 |

### Mon — Telfair

- Cluster **A**, 9 customers
- Centroid: 29.581, -95.6422
- Window: 3:00 PM – 7:00 PM
- Hero SKU: `honey-whole` → cake "Honey"

**Instagram post:**

```
HappyCake on the road — Mon afternoon in Telfair.
cake "Honey" fresh from the kitchen, plus the ready-made line — the original taste of happiness.
We park 3:00 PM – 7:00 PM; come grab a cake on the way home.
Order on the site at happycake.us or send a message on WhatsApp.
```

**WhatsApp templates (one per customer):**

- `+12815550111` (whatsapp):
  ```
  Hi Aaliyah! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have your usual cake "Honey" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550112` (whatsapp):
  ```
  Hi Bilqis! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Pistachio Roll" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550113` (whatsapp):
  ```
  Hi Carmen! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have your usual cake "Honey" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `@diana_cake` (instagram):
  ```
  Hi Diana! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Milk Maiden" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550115` (whatsapp):
  ```
  Hi Esra! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Napoleon" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `@farah_eats` (instagram):
  ```
  Hi Farah! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Honey" by the slice too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550141` (whatsapp):
  ```
  Hi Priya! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have your usual cake "Honey" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550142` (whatsapp):
  ```
  Hi Qadira! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Pistachio Roll" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550145` (whatsapp):
  ```
  Hi Tara! The HappyCake truck will be in Telfair this Mon, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Napoleon" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```

**Projection:** baseline 8.7 → projected 16.1 orders/mo (+7.4, +$278.20).

### Tue — Silverlake

- Cluster **B**, 5 customers
- Centroid: 29.557, -95.2934
- Window: 3:00 PM – 7:00 PM
- Hero SKU: `honey-whole` → cake "Honey"

**Instagram post:**

```
HappyCake on the road — Tue afternoon in Silverlake.
cake "Honey" fresh from the kitchen, plus the ready-made line — the original taste of happiness.
We park 3:00 PM – 7:00 PM; come grab a cake on the way home.
Order on the site at happycake.us or send a message on WhatsApp.
```

**WhatsApp templates (one per customer):**

- `+12815550151` (whatsapp):
  ```
  Hi Ulla! The HappyCake truck will be in Silverlake this Tue, 3:00 PM – 7:00 PM. We'll have your usual cake "Honey" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550152` (whatsapp):
  ```
  Hi Vesna! The HappyCake truck will be in Silverlake this Tue, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Pistachio Roll" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `@warda_h` (instagram):
  ```
  Hi Warda! The HappyCake truck will be in Silverlake this Tue, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Milk Maiden" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550154` (whatsapp):
  ```
  Hi Xenia! The HappyCake truck will be in Silverlake this Tue, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Napoleon" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550155` (whatsapp):
  ```
  Hi Yara! The HappyCake truck will be in Silverlake this Tue, 3:00 PM – 7:00 PM. We'll have your usual cake "Honey" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```

**Projection:** baseline 3.4 → projected 6.29 orders/mo (+2.89, +$119.09).

### Wed — Stafford

- Cluster **C**, 5 customers
- Centroid: 29.6166, -95.5739
- Window: 3:00 PM – 7:00 PM
- Hero SKU: `napoleon` → cake "Napoleon"

**Instagram post:**

```
HappyCake on the road — Wed afternoon in Stafford.
cake "Napoleon" fresh from the kitchen, plus the ready-made line — the original taste of happiness.
We park 3:00 PM – 7:00 PM; come grab a cake on the way home.
Order on the site at happycake.us or send a message on WhatsApp.
```

**WhatsApp templates (one per customer):**

- `+12815550124` (whatsapp):
  ```
  Hi Jasmin! The HappyCake truck will be in Stafford this Wed, 3:00 PM – 7:00 PM. We'll have your usual cake "Napoleon" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550131` (whatsapp):
  ```
  Hi Lina! The HappyCake truck will be in Stafford this Wed, 3:00 PM – 7:00 PM. We'll have cake "Napoleon" fresh and the ready-made line — your usual office dessert box too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `@maya_bakes` (instagram):
  ```
  Hi Maya! The HappyCake truck will be in Stafford this Wed, 3:00 PM – 7:00 PM. We'll have cake "Napoleon" fresh and the ready-made line — your usual cake "Honey" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550133` (whatsapp):
  ```
  Hi Noor! The HappyCake truck will be in Stafford this Wed, 3:00 PM – 7:00 PM. We'll have cake "Napoleon" fresh and the ready-made line — your usual cake "Milk Maiden" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550134` (whatsapp):
  ```
  Hi Olya! The HappyCake truck will be in Stafford this Wed, 3:00 PM – 7:00 PM. We'll have your usual cake "Napoleon" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```

**Projection:** baseline 5.3 → projected 9.8 orders/mo (+4.5, +$283.05).

### Thu — Sienna

- Cluster **D**, 4 customers
- Centroid: 29.517, -95.5343
- Window: 3:00 PM – 7:00 PM
- Hero SKU: `honey-whole` → cake "Honey"

**Instagram post:**

```
HappyCake on the road — Thu afternoon in Sienna.
cake "Honey" fresh from the kitchen, plus the ready-made line — the original taste of happiness.
We park 3:00 PM – 7:00 PM; come grab a cake on the way home.
Order on the site at happycake.us or send a message on WhatsApp.
```

**WhatsApp templates (one per customer):**

- `+12815550121` (whatsapp):
  ```
  Hi Gabriela! The HappyCake truck will be in Sienna this Thu, 3:00 PM – 7:00 PM. We'll have your usual cake "Honey" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550122` (whatsapp):
  ```
  Hi Hadia! The HappyCake truck will be in Sienna this Thu, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Milk Maiden" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `@ines_h` (instagram):
  ```
  Hi Ines! The HappyCake truck will be in Sienna this Thu, 3:00 PM – 7:00 PM. We'll have cake "Honey" fresh and the ready-made line — your usual cake "Pistachio Roll" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550125` (whatsapp):
  ```
  Hi Kamila! The HappyCake truck will be in Sienna this Thu, 3:00 PM – 7:00 PM. We'll have your usual cake "Honey" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```

**Projection:** baseline 3.9 → projected 7.22 orders/mo (+3.32, +$140.08).

### Fri — Aliana

- Cluster **E**, 2 customers
- Centroid: 29.6412, -95.7336
- Window: 3:00 PM – 7:00 PM
- Hero SKU: `milk-maiden` → cake "Milk Maiden"

**Instagram post:**

```
HappyCake on the road — Fri afternoon in Aliana.
cake "Milk Maiden" fresh from the kitchen, plus the ready-made line — the original taste of happiness.
We park 3:00 PM – 7:00 PM; come grab a cake on the way home.
Order on the site at happycake.us or send a message on WhatsApp.
```

**WhatsApp templates (one per customer):**

- `@rumi_cake` (instagram):
  ```
  Hi Rumi! The HappyCake truck will be in Aliana this Fri, 3:00 PM – 7:00 PM. We'll have cake "Milk Maiden" fresh and the ready-made line — your usual cake "Honey" too. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```
- `+12815550144` (whatsapp):
  ```
  Hi Sofia! The HappyCake truck will be in Aliana this Fri, 3:00 PM – 7:00 PM. We'll have your usual cake "Milk Maiden" fresh and the ready-made line. Reply if you'd like one set aside.
  Order on the site at happycake.us or send a message on WhatsApp.
  ```

**Projection:** baseline 1.9 → projected 3.52 orders/mo (+1.62, +$71.83).

## Owner approval

Before the truck rolls, the marketing agent posts this artifact to
Askhat in Telegram with inline approve / reject. On approve, the
Instagram post and per-customer WhatsApp templates are queued for the
sales agent to send through the existing channel handlers (no real
send is wired in this demo — every draft sits in `evidence/` for review).
