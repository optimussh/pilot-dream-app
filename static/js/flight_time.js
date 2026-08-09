/**
 * Phase-based flight time model (education default).
 *
 * Old model: time = distance / (cruise * 0.85)  → short hops unrealistically fast.
 * New model: taxi + climb + cruise + descent + approach, with lower speeds in
 * terminal phases. Short routes never reach full cruise (triangular profile).
 */
(function (global) {
  'use strict';

  /**
   * Performance profile by aircraft class (typical airliner ops averages).
   * Distances are ground track during climb/descent; avg speeds are lower than cruise.
   */
  function getPhaseProfile(aircraft) {
    const cat = String(aircraft.category || aircraft.type || '').toLowerCase();
    const name = String(aircraft.name || aircraft.id || '').toLowerCase();
    const type = String(aircraft.type || '').toLowerCase();
    const blob = `${cat} ${name} ${type}`;

    const isTurboprop =
      /atr|dash|q400|터보|turboprop|prop/.test(blob);
    const isRegional =
      /리저널|regional|embraer|e170|e175|e190|e195|crj|erj|mrj/.test(blob);
    const isWidebody =
      /중형|대형|광동|wide|777|787|747|767|a330|a340|a350|a380|b777|b787|b747|b767|dreamliner/.test(
        blob
      );

    if (isTurboprop) {
      return {
        classId: 'turboprop',
        classLabel: '터보프롭',
        climbDistKm: 80,
        descentDistKm: 70,
        climbAvgKmh: 320,
        descentAvgKmh: 340,
        taxiOutMin: 8,
        taxiInMin: 6,
        rollMin: 3,
        shortAvgKmh: 360,
        climbFuelMult: 1.25,
        minAirborneMin: 15,
      };
    }
    if (isRegional) {
      return {
        classId: 'regional',
        classLabel: '리저널 제트',
        climbDistKm: 140,
        descentDistKm: 130,
        climbAvgKmh: 450,
        descentAvgKmh: 480,
        taxiOutMin: 10,
        taxiInMin: 8,
        rollMin: 3,
        shortAvgKmh: 460,
        climbFuelMult: 1.28,
        minAirborneMin: 18,
      };
    }
    if (isWidebody) {
      return {
        classId: 'widebody',
        classLabel: '광동체',
        climbDistKm: 220,
        descentDistKm: 210,
        climbAvgKmh: 500,
        descentAvgKmh: 540,
        taxiOutMin: 15,
        taxiInMin: 12,
        rollMin: 4,
        shortAvgKmh: 480,
        climbFuelMult: 1.32,
        minAirborneMin: 22,
      };
    }
    // Default: narrow-body jet (B737 / A320 family)
    return {
      classId: 'narrowbody',
      classLabel: '협동체 제트',
      climbDistKm: 160,
      descentDistKm: 150,
      climbAvgKmh: 480,
      descentAvgKmh: 520,
      taxiOutMin: 12,
      taxiInMin: 9,
      rollMin: 3,
      shortAvgKmh: 470,
      climbFuelMult: 1.3,
      minAirborneMin: 18,
    };
  }

  function resolveCruiseKmh(aircraft) {
    const v =
      Number(aircraft.cruise_kmh) ||
      Number(aircraft.spd) ||
      Number(aircraft.speed) ||
      0;
    if (v > 100 && v < 1200) return v;
    return 820;
  }

  /**
   * Typical cruise flight level from sector length (ops rule of thumb).
   */
  function estimateCruiseFL(distanceKm) {
    const d = Math.max(0, distanceKm);
    if (d < 200) return 160 + Math.round(d / 40) * 10;
    if (d < 450) return 240 + Math.round((d - 200) / 50) * 10;
    if (d < 900) return 300 + Math.round((d - 450) / 90) * 10;
    if (d < 2500) return 340;
    if (d < 6000) return 360;
    return 380;
  }

  function formatHoursMinutes(hours) {
    const h = Math.floor(hours);
    let m = Math.round((hours - h) * 60);
    if (m === 60) {
      return { hours: h + 1, mins: 0, text: `${h + 1}시간 0분` };
    }
    if (h <= 0) {
      return { hours: 0, mins: m, text: `${m}분` };
    }
    return { hours: h, mins: m, text: `${h}시간 ${m}분` };
  }

  /**
   * @param {number} distanceKm great-circle distance
   * @param {object} aircraft aircraft catalog row
   * @param {number} [weatherFactor=1] routing / holding multiplier (1.0 clear)
   * @returns {object} block/airborne times and phase breakdown
   */
  function estimateFlightTime(distanceKm, aircraft, weatherFactor) {
    const dist = Math.max(0, Number(distanceKm) || 0);
    const weather = Math.max(1, Number(weatherFactor) || 1);
    const profile = getPhaseProfile(aircraft || {});
    const cruiseKmh = resolveCruiseKmh(aircraft || {});
    const terminalKm = profile.climbDistKm + profile.descentDistKm;

    let climbKm;
    let descentKm;
    let cruiseKm;
    let climbH;
    let descentH;
    let cruiseH;
    let mode;

    if (dist >= terminalKm) {
      // Full profile: climb → cruise → descent
      mode = 'cruise';
      climbKm = profile.climbDistKm;
      descentKm = profile.descentDistKm;
      cruiseKm = dist - climbKm - descentKm;
      climbH = climbKm / profile.climbAvgKmh;
      descentH = descentKm / profile.descentAvgKmh;
      cruiseH = cruiseKm / cruiseKmh;
    } else {
      // Short hop: no sustained cruise (triangular climb/descent)
      mode = 'short';
      const fill = Math.max(0.12, Math.min(1, dist / terminalKm));
      const ratio = profile.climbDistKm / terminalKm;
      climbKm = dist * ratio;
      descentKm = dist - climbKm;
      cruiseKm = 0;
      // Lower intermediate altitude → slightly lower phase speeds
      const climbSpd = profile.climbAvgKmh * (0.72 + 0.28 * fill);
      const descentSpd = profile.descentAvgKmh * (0.78 + 0.22 * fill);
      climbH = climbKm > 0 ? climbKm / climbSpd : 0;
      descentH = descentKm > 0 ? descentKm / descentSpd : 0;
      cruiseH = 0;

      // Floor: very short sectors still need circuit / SID-STAR time
      const minAir = profile.minAirborneMin / 60;
      const effAvg = profile.shortAvgKmh * (0.52 + 0.48 * fill);
      const avgBased = dist > 0 ? dist / Math.max(200, effAvg) : 0;
      const phaseSum = climbH + descentH;
      const airborneCore = Math.max(phaseSum, avgBased, dist > 0 ? minAir : 0);
      // Redistribute so UI phases still sum sensibly
      if (phaseSum > 0 && airborneCore > phaseSum) {
        const scale = airborneCore / phaseSum;
        climbH *= scale;
        descentH *= scale;
      } else if (phaseSum === 0 && dist > 0) {
        climbH = airborneCore * 0.5;
        descentH = airborneCore * 0.5;
      }
    }

    const rollH = profile.rollMin / 60;
    let airborneClean = climbH + cruiseH + descentH + rollH;
    // Absolute minimum airborne for any airborne jet sector
    if (dist > 0) {
      airborneClean = Math.max(airborneClean, profile.minAirborneMin / 60);
    }

    const taxiOutH = profile.taxiOutMin / 60;
    const taxiInH = profile.taxiInMin / 60;
    // Weather/holding mainly stretches airborne, not gate taxi
    const airborneH = airborneClean * weather;
    const blockH = taxiOutH + airborneH + taxiInH;

    const naiveCruiseOnlyH =
      dist > 0 ? dist / (cruiseKmh * 0.85) : 0; // old model for comparison
    const effectiveBlockKmh = blockH > 0 ? dist / blockH : 0;
    const cruiseFL = estimateCruiseFL(dist);

    const fmt = formatHoursMinutes(blockH);

    return {
      distanceKm: dist,
      cruiseKmh,
      weatherFactor: weather,
      mode,
      profile,
      climbKm: Math.round(climbKm),
      cruiseKm: Math.round(cruiseKm),
      descentKm: Math.round(descentKm),
      climbH,
      cruiseH,
      descentH,
      rollH,
      taxiOutH,
      taxiInH,
      airborneH,
      blockH,
      hours: fmt.hours,
      mins: fmt.mins,
      timeText: fmt.text,
      effectiveBlockKmh: Math.round(effectiveBlockKmh),
      naiveCruiseOnlyH,
      cruiseFL,
      hasCruise: cruiseKm > 1,
    };
  }

  /**
   * Fuel with climb/descent burn premium (kg).
   * catalog fuel_burn is treated as cruise kg/km average.
   */
  function estimateFuelKg(distanceKm, aircraft, loadFactor, weatherFactor, timeModel) {
    const burn = Number(aircraft.fuel_burn) || 3.5;
    const load = Number(loadFactor) || 1;
    const weather = Math.max(1, Number(weatherFactor) || 1);
    const model =
      timeModel || estimateFlightTime(distanceKm, aircraft, weatherFactor);
    const mult = model.profile.climbFuelMult;
    const climbDescKm = model.climbKm + model.descentKm;
    const cruiseKm = model.cruiseKm;
    const fuelKg =
      (climbDescKm * burn * mult + cruiseKm * burn) * load * weather;
    return Math.max(0, fuelKg);
  }

  global.FlightTimeModel = {
    getPhaseProfile,
    resolveCruiseKmh,
    estimateCruiseFL,
    estimateFlightTime,
    estimateFuelKg,
    formatHoursMinutes,
  };
})(typeof window !== 'undefined' ? window : globalThis);
