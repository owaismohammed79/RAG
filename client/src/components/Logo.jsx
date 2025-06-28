
function Logo({className='', textSize='2xl'}) {
  return (
    <div className={`w-28 flex items-center justify-center bg-transparent gap-1 px-1 px-2 mt-1 ${className}`}>
        <div className="overflow-hidden">
            <img src="/RAG-logo.png" alt="logo" className="block max-w-full"/>
        </div>
        <span className={`text-2xl font-bold text-white text-${textSize}`}>RAG</span>
    </div>
  )
}

export default Logo