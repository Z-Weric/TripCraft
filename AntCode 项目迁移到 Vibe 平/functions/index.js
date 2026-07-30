import { Hono } from 'hono';
import itineraryRouter from './itineraryRouter.js';

const app = new Hono();

// 挂载攻略核心路由。注意，Vibe 前端通过 vibeSdk.functions.get/post('itinerary/xxx') 会自动匹配到这里
app.route('/itinerary', itineraryRouter);

app.get('/ping', (c) => c.text('Welcome to TripCraft'));

app.notFound((c) => c.json({ error: 'Not Found' }, 404));

export default app;