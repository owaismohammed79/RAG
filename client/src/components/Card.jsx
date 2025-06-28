import React from 'react'

function Card({header='', content='',imgUrl, borderPosition, className}) {
  return (
    <div className={`bg-[#0A363CB2] border ${className} flex flex-col mx-1 my-2`}>
        <h2 className='text-3xl'>{header}</h2>
        <p className='text-lg text-center'>{content}</p>
        <img src={imgUrl} alt={header} className='w-full h-60 object-cover'/>
    </div>
  )
}

export default Card