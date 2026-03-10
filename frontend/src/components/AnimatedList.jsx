import { useRef, useState, useEffect, useCallback } from "react"
import { motion, useInView } from "framer-motion"
import "./AnimatedList.css"

const AnimatedItem = ({ children, index, delay = 0, onMouseEnter, onClick }) => {
  const ref = useRef(null)
  const inView = useInView(ref, { amount: 0.5 })

  return (
    <motion.div
      ref={ref}
      data-index={index}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={inView ? { opacity: 1, scale: 1 } : {}}
      transition={{ duration: 0.25, delay }}
      onMouseEnter={onMouseEnter}
      onClick={onClick}
      style={{ marginBottom: "1rem", cursor: "pointer" }}
    >
      {children}
    </motion.div>
  )
}

export default function AnimatedList({
  items = [],
  onItemSelect
}) {

  const listRef = useRef(null)
  const [selectedIndex, setSelectedIndex] = useState(-1)

  const handleItemClick = useCallback((item, index) => {
    setSelectedIndex(index)
    if (onItemSelect) onItemSelect(item, index)
  }, [])

  return (
    <div className="scroll-list-container">

      <div ref={listRef} className="scroll-list">

        {items.map((item, index) => (
          <AnimatedItem
            key={index}
            index={index}
            delay={index * 0.05}
            onClick={() => handleItemClick(item, index)}
          >
            <div className={`item ${selectedIndex === index ? "selected" : ""}`}>
              <p>{item}</p>
            </div>
          </AnimatedItem>
        ))}

      </div>

    </div>
  )
}
