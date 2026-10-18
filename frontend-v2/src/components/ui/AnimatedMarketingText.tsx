import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const WORDS = ['Autonomous.', 'Orchestrated.', 'Optimized.', 'Protected.'];

export function AnimatedMarketingText() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1) % WORDS.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative h-[50px] sm:h-[70px] md:h-[90px] lg:h-[110px] w-full flex justify-center items-center overflow-hidden text-primary">
      <AnimatePresence mode="popLayout">
        <motion.div
          key={index}
          initial={{ y: 80, opacity: 0, rotateX: -90 }}
          animate={{ y: 0, opacity: 1, rotateX: 0 }}
          exit={{ y: -80, opacity: 0, rotateX: 90 }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
          className="absolute whitespace-nowrap origin-center"
          style={{ transformStyle: 'preserve-3d' }}
        >
          {WORDS[index]}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
