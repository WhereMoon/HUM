import { useEffect, useRef, useState } from 'react'
import * as PIXI from 'pixi.js'
// 使用 Cubism 4 版本（支持 Cubism 3/4/5 模型）
import { Live2DModel } from 'pixi-live2d-display/cubism4'
import './Live2DStage.css'

// 确保 Cubism 核心库已加载
declare global {
  interface Window {
    Live2DCubismCore: any
    PIXI: any 
  }
}

// 终极 Hack：拦截 WebGL 的参数查询，强制修复 checkMaxIfStatementsInShader 错误
// 这个错误是由于某些环境下 gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS) 返回 0 导致的
try {
    const patchGetParameter = (proto: any) => {
        if (!proto || !proto.getParameter || proto.getParameter.__patched) return;
        const originalGetParameter = proto.getParameter;
        proto.getParameter = function(parameter: number) {
            const value = originalGetParameter.call(this, parameter);
            // 0x8DF2 是 MAX_FRAGMENT_UNIFORM_VECTORS 的常量值
            if (parameter === 0x8DF2 && value === 0) {
                console.warn('WebGL reported 0 for MAX_FRAGMENT_UNIFORM_VECTORS, patching to 128');
                return 128;
            }
            return value;
        };
        proto.getParameter.__patched = true;
    };
    
    // @ts-ignore
    patchGetParameter(window.WebGLRenderingContext?.prototype);
    // @ts-ignore
    patchGetParameter(window.WebGL2RenderingContext?.prototype);
} catch (e) {
    console.error('Failed to patch WebGL getParameter:', e);
}

interface Live2DStageProps {
  clientId: string
  expression?: string
  onModelLoaded?: () => void
}

const Live2DStage: React.FC<Live2DStageProps> = ({ 
  clientId, 
  expression = 'idle',
  onModelLoaded 
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const appRef = useRef<PIXI.Application | null>(null)
  const modelRef = useRef<Live2DModel | null>(null)
  const expressionRef = useRef<string>(expression)
  const [isLoaded, setIsLoaded] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    expressionRef.current = expression
    if (modelRef.current) {
      updateExpression(expression)
    }
  }, [expression])

  useEffect(() => {
    let isMounted = true;
    if (!canvasRef.current) return;

    console.log('Initializing PIXI Application (v6 stable)...')

    const init = async () => {
      try {
        // 1. 暴露 PIXI 到全局 (Live2D 插件需要)
        (window as any).PIXI = PIXI;
        
        // 2. 注册 Ticker (Live2DModel 需要)
        Live2DModel.registerTicker(PIXI.Ticker);

        // 3. 初始化 PIXI 应用 (v6 语法)
        const app = new PIXI.Application({
          view: canvasRef.current!,
          backgroundAlpha: 0, // 使用新属性名避免警告
          backgroundColor: 0x000000,
          resizeTo: canvasRef.current!.parentElement || window,
          antialias: true,
          autoStart: true
        });

        appRef.current = app;
        
        if (!isMounted) {
            app.destroy(true, { children: true, texture: true });
            return;
        }

        // 4. 加载模型
        await loadLive2DModel(app, () => isMounted);
        
      } catch (error) {
        console.error('Failed to initialize PIXI:', error);
        if (isMounted) {
            setErrorMsg(`PIXI 初始化失败: ${error}`);
        }
      }
    }

    // 稍微延迟初始化，避开 React 严格模式下的二次挂载干扰
    const timer = setTimeout(init, 100);

    return () => {
      clearTimeout(timer);
      isMounted = false;
      if (appRef.current) {
        appRef.current.destroy(true, { children: true, texture: true })
        appRef.current = null;
      }
    }
  }, [])

  const loadLive2DModel = async (app: PIXI.Application, isMounted: () => boolean) => {
    if (!app || !app.stage) return;
    
    try {
      // 等待 Cubism Core 加载
      let retries = 50
      while (!window.Live2DCubismCore && retries > 0) {
        if (!isMounted()) return;
        await new Promise(resolve => setTimeout(resolve, 100))
        retries--
      }
      
      if (!isMounted()) return;

      if (!window.Live2DCubismCore) {
        throw new Error('Live2D Cubism Core not loaded');
      }
      
      const modelPath = '/models/CubismSdkForWeb-5-r.4/Samples/Resources/Haru/Haru.model3.json'
      console.log('Loading Live2D model from:', modelPath)
      
      try {
        const model = await Live2DModel.from(modelPath)
        
        if (!isMounted()) return;

        // 缩放和定位
        const width = app.screen.width;
        const height = app.screen.height;

        const scale = Math.min(
          width / model.width,
          height / model.height
        ) * 0.8
        
        model.scale.set(scale)
        model.x = width / 2
        model.y = height / 2
        model.anchor.set(0.5, 0.5)

        app.stage.addChild(model as any)
        modelRef.current = model

        console.log('Model added to stage')
        startIdleAnimation(model)
        
        // 监听 resize 事件，动态调整模型位置
        const resizeModel = () => {
            const w = app.screen.width;
            const h = app.screen.height;
            
            // 重新计算缩放比例
            const s = Math.min(
                w / model.width,
                h / model.height
            ) * 0.8; // 保持 80% 的视口填充率
            
            model.scale.set(s);
            model.x = w * 0.5;
            // 将模型垂直中心稍微下移一点，避免头部被截断，因为模型中心点通常在身体中部
            model.y = h * 0.55; 
        };
        
        // 立即执行一次
        resizeModel();
        
        // 绑定到 renderer 的 resize 事件
        app.renderer.on('resize', resizeModel);
        
        setIsLoaded(true)
        onModelLoaded?.()
        
      } catch (error) {
        console.error('Live2D model loading error:', error)
        if (isMounted()) {
            createPlaceholder(app)
            setIsLoaded(true)
            onModelLoaded?.()
        }
      }
    } catch (error) {
      console.error('Failed to load Live2D model:', error)
      if (isMounted()) {
          createPlaceholder(app)
          setIsLoaded(true)
          onModelLoaded?.()
      }
    }
  }

  const createPlaceholder = (app: PIXI.Application) => {
    const graphics = new PIXI.Graphics()
    graphics.beginFill(0xffffff)
    graphics.drawCircle(0, 0, 100)
    graphics.endFill()
    
    const width = app.screen.width;
    const height = app.screen.height;

    graphics.x = width / 2
    graphics.y = height / 2
    app.stage.addChild(graphics as any)
    
    const text = new PIXI.Text('Live2D Model\nLoading Failed', {
        fontFamily: 'Arial',
        fontSize: 24,
        fill: 0xffffff,
        align: 'center',
    })
    text.anchor.set(0.5)
    text.x = width / 2
    text.y = height / 2 + 150
    app.stage.addChild(text as any)
  }

  const updateExpression = (newExpression: string) => {
    if (!modelRef.current) return

    const expressionMap: Record<string, { param: string; value: number }[]> = {
      smile: [{ param: 'ParamMouthOpenY', value: 0.5 }],
      sad: [{ param: 'ParamBrowLY', value: -0.3 }, { param: 'ParamBrowRY', value: -0.3 }],
      worried: [{ param: 'ParamBrowLX', value: 0.2 }, { param: 'ParamBrowRX', value: -0.2 }],
      angry: [{ param: 'ParamBrowLY', value: 0.3 }, { param: 'ParamBrowRY', value: 0.3 }],
      idle: []
    }

    const params = expressionMap[newExpression] || []
    params.forEach(({ param, value }) => {
      try {
        modelRef.current?.internalModel.coreModel.setParameterValueById(param, value)
      } catch (e) { }
    })
  }

  const startIdleAnimation = (model: Live2DModel) => {
    let time = 0
    const animate = () => {
      if (!modelRef.current) return
      if (expressionRef.current === 'idle') {
          time += 0.02
      }
      requestAnimationFrame(animate)
    }
    animate()
  }

  const handleLipSync = (audioData: ArrayBuffer) => {
    if (!modelRef.current) return

    const audioContext = new AudioContext()
    audioContext.decodeAudioData(audioData.slice(0))
      .then(audioBuffer => {
        const data = audioBuffer.getChannelData(0)
        const rms = Math.sqrt(
          data.reduce((sum, val) => sum + val * val, 0) / data.length
        )
        const mouthOpen = Math.min(rms * 10, 1)
        
        try {
          modelRef.current?.internalModel.coreModel.setParameterValueById(
            'ParamMouthOpenY',
            mouthOpen
          )
        } catch (e) { }
      })
      .catch(err => console.error('Audio decode error:', err))
  }

  useEffect(() => {
    if (canvasRef.current) {
      ;(canvasRef.current as any).handleLipSync = handleLipSync
    }
  }, [])

  return (
    <div className="live2d-stage-container">
      <canvas ref={canvasRef} className="live2d-canvas" />
      {!isLoaded && !errorMsg && (
        <div className="loading-placeholder">
          <p>加载数字人模型中...</p>
        </div>
      )}
      {errorMsg && (
        <div className="error-display">
            <p>{errorMsg}</p>
        </div>
      )}
    </div>
  )
}

export default Live2DStage
