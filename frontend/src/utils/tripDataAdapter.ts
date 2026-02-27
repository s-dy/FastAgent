/**
 * 后端 → 前端数据适配工具
 *
 * 后端与前端的字段名 / 结构存在以下差异，本模块统一处理：
 *
 * Location:  longitude/latitude  →  lng/lat
 * Attraction:
 *   - visit_duration (分钟)     →  suggested_duration_hours (小时)
 *   - category                  →  type
 *   - image_url (单个字符串)    →  image_urls (字符串数组)
 * Meal → Dining:
 *   - estimated_cost            →  cost_per_person
 *   - 列表字段名 dining        →  dinings
 * Hotel:
 *   - price_range / estimated_cost  →  price
 *   - distance                      →  distance_to_main_attraction_km
 *   - 每日 hotels[]                 →  recommended_hotel (取首个)
 * Weather:
 *   - wind_direction            →  day_wind
 *   - wind_power                →  night_wind
 */
import type { Location, TripPlanResponse, Attraction, Dining, Hotel, Weather } from '@/types'

/**
 * 标准化位置坐标：兼容后端 longitude/latitude 和前端 lng/lat 两种格式
 */
export const normalizeLocation = (location: any): Location | undefined => {
  if (!location) return undefined
  const lat = parseFloat(location.lat ?? location.latitude)
  const lng = parseFloat(location.lng ?? location.longitude)
  if (isNaN(lat) || isNaN(lng)) return undefined
  return { lat, lng }
}

/**
 * 适配景点：后端 Attraction → 前端 Attraction
 */
const normalizeAttraction = (attraction: any): Attraction => {
  // visit_duration(分钟) → suggested_duration_hours(小时)
  const suggestedDurationHours =
    attraction.suggested_duration_hours ??
    (attraction.visit_duration ? attraction.visit_duration / 60 : null)

  // category → type
  const type = attraction.type ?? attraction.category ?? '景点'

  // image_url(单个) → image_urls(数组)
  let imageUrls = attraction.image_urls
  if (!Array.isArray(imageUrls)) {
    const singleUrl = attraction.image_url || attraction.image_urls
    imageUrls = singleUrl ? [singleUrl] : []
  }

  return {
    ...attraction,
    type,
    suggested_duration_hours: suggestedDurationHours,
    image_urls: imageUrls,
    location: normalizeLocation(attraction.location),
    ticket_price: attraction.ticket_price ?? 0,
    rating: attraction.rating ?? 'N/A'
  }
}

/**
 * 适配餐饮：后端 Meal → 前端 Dining
 */
const normalizeDining = (dining: any): Dining => {
  // estimated_cost → cost_per_person
  const costPerPerson = dining.cost_per_person ?? dining.estimated_cost ?? 0

  return {
    ...dining,
    cost_per_person: costPerPerson,
    address: dining.address ?? '',
    rating: dining.rating ?? 'N/A',
    location: normalizeLocation(dining.location)
  }
}

/**
 * 适配酒店：后端 Hotel → 前端 Hotel
 */
const normalizeHotel = (hotel: any): Hotel => {
  // price_range / estimated_cost → price
  let price: number | string = hotel.price ?? hotel.estimated_cost ?? hotel.price_range ?? ''
  if (typeof price === 'string' && price !== '') {
    const numericMatch = price.match(/(\d+(\.\d+)?)/)
    if (numericMatch) {
      price = parseFloat(numericMatch[1])
    }
  }

  // distance → distance_to_main_attraction_km
  let distanceKm = hotel.distance_to_main_attraction_km ?? null
  if (distanceKm == null && hotel.distance) {
    const distStr = String(hotel.distance)
    const distMatch = distStr.match(/([\d.]+)/)
    if (distMatch) {
      distanceKm = parseFloat(distMatch[1])
    }
  }

  return {
    ...hotel,
    price,
    rating: hotel.rating ?? 'N/A',
    distance_to_main_attraction_km: distanceKm,
    location: normalizeLocation(hotel.location)
  }
}

/**
 * 适配天气：后端 WeatherInfo → 前端 Weather
 */
const normalizeWeather = (weather: any): Weather | undefined => {
  if (!weather) return undefined
  return {
    ...weather,
    date: weather.date ?? '',
    day_weather: weather.day_weather ?? '',
    night_weather: weather.night_weather ?? '',
    day_temp: String(weather.day_temp ?? ''),
    night_temp: String(weather.night_temp ?? ''),
    day_wind: weather.day_wind ?? weather.wind_direction ?? null,
    night_wind: weather.night_wind ?? weather.wind_power ?? null
  }
}

/**
 * 适配后端返回的行程数据，统一字段名和数据格式
 */
export const sanitizeTripPlan = (plan: any): TripPlanResponse => {
  const sanitizedDays = (plan.days || []).map((day: any) => {
    // 适配景点
    const attractions = (day.attractions || []).map(normalizeAttraction)

    // 适配餐饮：后端字段名 dining，前端使用 dinings
    const rawDinings = day.dinings || day.dining || []
    const dinings = rawDinings.map(normalizeDining)

    // 适配酒店：后端字段名 hotels（列表），前端使用 recommended_hotel（单个）
    let recommendedHotel = day.recommended_hotel || null
    if (!recommendedHotel && Array.isArray(day.hotels) && day.hotels.length > 0) {
      recommendedHotel = day.hotels[0]
    }
    if (recommendedHotel) {
      recommendedHotel = normalizeHotel(recommendedHotel)
    }

    // 适配天气
    const weather = normalizeWeather(day.weather)

    return {
      ...day,
      attractions,
      dinings,
      weather,
      recommended_hotel: recommendedHotel,
      budget: day.budget || { transport_cost: 0, dining_cost: 0, hotel_cost: 0, attraction_ticket_cost: 0, total: 0 }
    }
  })

  // 适配顶层酒店列表
  const hotels = (plan.hotels || []).map(normalizeHotel)

  return {
    ...plan,
    days: sanitizedDays,
    hotels
  }
}
