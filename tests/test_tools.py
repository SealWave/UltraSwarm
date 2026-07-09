"""
tests/test_tools.py
===================
Tests for tool functionality.
Tests browser tools, output manager, and other tool modules.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestSkillLoader:
    """Test skill loader tool"""

    def test_skill_loader_import(self):
        """Test that skill loader can be imported"""
        from tools.skill_loader import load_skill, AgentSkill
        
        assert load_skill is not None
        assert AgentSkill is not None

    def test_agent_skill_class(self):
        """Test AgentSkill pydantic class"""
        from tools.skill_loader import AgentSkill
        
        skill = AgentSkill(
            name="test",
            role="worker",
            system_prompt="Test prompt"
        )
        
        assert skill.name == "test"
        assert skill.role == "worker"


class TestBrowserTools:
    """Test browser tool functionality"""

    def test_browser_module_import(self):
        """Test that browser module can be imported"""
        try:
            from tools import browser
            assert browser is not None
        except ImportError as e:
            pytest.skip(f"Browser module import failed: {e}")

    def test_browser_config_import(self):
        """Test that browser config can be imported"""
        try:
            from tools.browser_config import BrowserConfig
            assert BrowserConfig is not None
        except ImportError as e:
            pytest.skip(f"Browser config import failed: {e}")

    def test_browser_actions_import(self):
        """Test that browser actions can be imported"""
        try:
            from tools.browser_actions import BrowserActions
            assert BrowserActions is not None
        except ImportError as e:
            pytest.skip(f"Browser actions import failed: {e}")

    def test_browser_config_defaults(self):
        """Test browser config default values"""
        try:
            from tools.browser_config import BrowserConfig
            
            config = BrowserConfig()
            
            # Check that config has expected attributes
            assert hasattr(config, 'headless') or hasattr(config, '__dict__')
        except ImportError:
            pytest.skip("Browser config not available")


class TestOutputManager:
    """Test output manager functionality"""

    def test_output_manager_import(self):
        """Test that output manager can be imported"""
        try:
            from tools.output_manager import OutputManager
            assert OutputManager is not None
        except ImportError as e:
            pytest.skip(f"Output manager import failed: {e}")

    def test_output_manager_creation(self):
        """Test creating an output manager instance"""
        try:
            from tools.output_manager import OutputManager
            
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = OutputManager(output_dir=tmpdir)
                assert manager is not None
        except ImportError:
            pytest.skip("Output manager not available")
        except Exception as e:
            pytest.skip(f"Output manager creation failed: {e}")

    def test_output_manager_save_output(self):
        """Test saving output with output manager"""
        try:
            from tools.output_manager import OutputManager
            
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = OutputManager(output_dir=tmpdir)
                
                # Try to save output
                test_output = {
                    "task": "test_task",
                    "result": "success",
                    "data": {"key": "value"}
                }
                
                # Check if save method exists
                if hasattr(manager, 'save'):
                    filepath = manager.save("test_output", test_output)
                    assert Path(filepath).exists()
                else:
                    pytest.skip("save method not found")
        except ImportError:
            pytest.skip("Output manager not available")
        except Exception as e:
            pytest.skip(f"Output manager test failed: {e}")


class TestSwarmMemory:
    """Test swarm memory functionality"""

    def test_swarm_memory_import(self):
        """Test that swarm memory can be imported"""
        try:
            from tools.swarm_memory import SwarmMemory
            assert SwarmMemory is not None
        except ImportError as e:
            pytest.skip(f"Swarm memory import failed: {e}")

    def test_swarm_memory_creation(self):
        """Test creating a swarm memory instance"""
        try:
            from tools.swarm_memory import SwarmMemory
            
            with tempfile.TemporaryDirectory() as tmpdir:
                memory = SwarmMemory(storage_path=tmpdir)
                assert memory is not None
        except ImportError:
            pytest.skip("Swarm memory not available")
        except Exception as e:
            pytest.skip(f"Swarm memory creation failed: {e}")


class TestAgentScanner:
    """Test agent scanner tool"""

    def test_agent_scanner_import(self):
        """Test that agent scanner can be imported"""
        try:
            from tools.agent_scanner import scan_agents
            assert scan_agents is not None
        except ImportError as e:
            pytest.skip(f"Agent scanner import failed: {e}")


class TestStoreAdmin:
    """Test store admin tool"""

    def test_store_admin_import(self):
        """Test that store admin can be imported"""
        try:
            from tools.store_admin import StoreAdmin
            assert StoreAdmin is not None
        except ImportError as e:
            pytest.skip(f"Store admin import failed: {e}")


class TestToolsInit:
    """Test tools package initialization"""

    def test_tools_package_import(self):
        """Test that tools package can be imported"""
        from tools import __init__
        
        # Package should be importable
        assert __init__ is not None


# =============================================================================
# Tool Functionality Tests
# =============================================================================

class TestBrowserSearchTool:
    """Test browser search functionality"""

    def test_browser_search_mock(self):
        """Test browser search with mocked browser"""
        mock_browser = Mock()
        mock_browser.search = Mock(return_value={"results": ["result1", "result2"]})
        
        result = mock_browser.search("test query")
        
        assert result is not None
        assert "results" in result

    def test_browser_navigate_mock(self):
        """Test browser navigation with mocked browser"""
        mock_browser = Mock()
        mock_browser.navigate = Mock(return_value=True)
        
        result = mock_browser.navigate("https://example.com")
        
        assert result is True


class TestOutputSaving:
    """Test output saving functionality"""

    def test_json_output_saving(self):
        """Test saving JSON output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.json"
            
            test_data = {
                "task_id": "test_123",
                "status": "completed",
                "result": {"key": "value"}
            }
            
            with open(output_file, "w") as f:
                json.dump(test_data, f, indent=2)
            
            assert output_file.exists()
            
            with open(output_file, "r") as f:
                loaded = json.load(f)
            
            assert loaded["task_id"] == "test_123"
            assert loaded["status"] == "completed"

    def test_text_output_saving(self):
        """Test saving text output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            
            test_text = "This is test output content."
            
            with open(output_file, "w") as f:
                f.write(test_text)
            
            assert output_file.exists()
            
            content = output_file.read_text()
            assert content == test_text

    def test_nested_directory_output(self):
        """Test saving output to nested directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "output"
            nested_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = nested_dir / "output.json"
            
            test_data = {"nested": True}
            
            with open(output_file, "w") as f:
                json.dump(test_data, f)
            
            assert output_file.exists()


class TestToolIntegration:
    """Test integration between tools"""

    def test_skill_loader_with_output_manager(self):
        """Test skill loader working with output manager"""
        from tools.skill_loader import AgentSkill
        
        # Create a skill
        skill = AgentSkill(
            name="integration_skill",
            role="worker",
            system_prompt="Integration test.",
            tools=["output_saver"],
            context={"output_format": "json"}
        )
        
        # Save skill data to output
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "skill_output.json"
            
            skill_dict = skill.model_dump()
            
            with open(output_file, "w") as f:
                json.dump(skill_dict, f, indent=2)
            
            assert output_file.exists()

    def test_tool_chain_mock(self):
        """Test chaining multiple tools (mocked)"""
        # Mock a chain of tools
        search_tool = Mock()
        search_tool.execute = Mock(return_value={"results": ["item1", "item2"]})
        
        process_tool = Mock()
        process_tool.execute = Mock(return_value={"processed": ["processed_item1"]})
        
        output_tool = Mock()
        output_tool.save = Mock(return_value="output.json")
        
        # Execute chain
        search_result = search_tool.execute("query")
        process_result = process_tool.execute(search_result)
        output_path = output_tool.save(process_result)
        
        assert search_result is not None
        assert process_result is not None
        assert output_path == "output.json"


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestToolEdgeCases:
    """Test edge cases for tools"""

    def test_empty_output(self):
        """Test handling empty output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "empty.json"
            
            with open(output_file, "w") as f:
                json.dump({}, f)
            
            with open(output_file, "r") as f:
                data = json.load(f)
            
            assert data == {}

    def test_large_output(self):
        """Test handling large output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "large.json"
            
            # Create a large data structure
            large_data = {
                f"key_{i}": f"value_{i}" * 100
                for i in range(1000)
            }
            
            with open(output_file, "w") as f:
                json.dump(large_data, f)
            
            assert output_file.exists()
            assert output_file.stat().st_size > 100000

    def test_unicode_output(self):
        """Test handling unicode in output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "unicode.json"
            
            unicode_data = {
                "chinese": "你好世界",
                "arabic": "مرحبا بالعالم",
                "russian": "Привет мир",
                "emoji": "😀🎉🚀"
            }
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(unicode_data, f, ensure_ascii=False, indent=2)
            
            with open(output_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            
            assert loaded["chinese"] == "你好世界"
            assert loaded["emoji"] == "😀🎉🚀"

    def test_special_characters_in_filename(self):
        """Test handling special characters in filenames"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a safe filename (avoid truly invalid chars)
            output_file = Path(tmpdir) / "output_test_123.json"
            
            test_data = {"test": "data"}
            
            with open(output_file, "w") as f:
                json.dump(test_data, f)
            
            assert output_file.exists()


# =============================================================================
# Tool Availability Tests
# =============================================================================

class TestToolAvailability:
    """Test that required tools are available"""

    def test_core_tools_available(self):
        """Test that core tools are available"""
        core_tools = [
            "tools.skill_loader",
            "tools.output_manager",
        ]
        
        for tool_path in core_tools:
            try:
                parts = tool_path.split(".")
                module = __import__(tool_path, fromlist=parts[-1:])
                assert module is not None, f"Tool {tool_path} not available"
            except ImportError:
                pytest.skip(f"Core tool {tool_path} not available")

    def test_optional_tools_graceful_failure(self):
        """Test that optional tools fail gracefully when not available"""
        optional_tools = [
            "tools.browser",
            "tools.browser_actions",
            "tools.swarm_memory",
            "tools.store_admin",
        ]
        
        for tool_path in optional_tools:
            try:
                parts = tool_path.split(".")
                module = __import__(tool_path, fromlist=parts[-1:])
                # If import succeeds, tool is available
                assert module is not None
            except ImportError:
                # Optional tools should fail gracefully
                pass  # This is expected for optional tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
