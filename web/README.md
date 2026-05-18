# NetSim Web

Next.js 15 + TypeScript + Tailwind + deck.gl + Mapbox. Renders the carrier network map and the agent chat panel.

```bash
npm install
echo "NEXT_PUBLIC_MAPBOX_TOKEN=..." > .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> .env.local
npm run dev
```

Visit `http://localhost:3000` and click into a featured carrier.
