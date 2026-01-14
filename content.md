#### Acts 1: 使性能分析脚本能够处理中断

我们将修改 `profile_stitcher.py`，确保即使在被打断时也能生成报告。

~~~~~act
patch_file
scripts/profile_stitcher.py
~~~~~
~~~~~python.old
    profiler = Profiler(interval=0.001)
    profiler.start()

    print(f"🚀 Profiling 'stitcher {args.command}'...")
    try:
        target_action()
    except Exception as e:
        print(f"❌ Command failed during profiling: {e}")
    finally:
        profiler.stop()
~~~~~
~~~~~python.new
    profiler = Profiler(interval=0.001)
    
    print(f"🚀 Profiling 'stitcher {args.command}'...")
    profiler.start()
    try:
        target_action()
    except KeyboardInterrupt:
        print("\n🛑 Profiling interrupted by user. Generating report...")
    except Exception as e:
        print(f"❌ Command failed during profiling: {e}")
    finally:
        profiler.stop()
~~~~~
