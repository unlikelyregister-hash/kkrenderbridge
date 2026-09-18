using System;
using System.Reflection;
using KKAPI.Maker;
using UnityEngine;

namespace KkRenderBridge
{
    // Called from Awake() after plugin init — dumps MakerAPI surface
    public static class MakerApiProbe
    {
        public static void Dump()
        {
            var type = typeof(MakerAPI);
            Debug.Log("[KkRenderBridge] === MakerAPI methods ===");
            foreach (var m in type.GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly))
            {
                string ps = "";
                foreach (var p in m.GetParameters()) ps += (ps.Length > 0 ? ", " : "") + p.ParameterType.Name + " " + p.Name;
                string mb = m.IsStatic ? "static " : "";
                Debug.Log("[KkRenderBridge]   " + mb + m.ReturnType.Name + " " + m.Name + "(" + ps + ")");
            }
            Debug.Log("[KkRenderBridge] === MakerAPI properties ===");
            foreach (var p in type.GetProperties(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                Debug.Log("[KkRenderBridge]   " + p.PropertyType.Name + " " + p.Name);
            Debug.Log("[KkRenderBridge] === Load methods ===");
            foreach (var m in type.GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                if (m.Name.ToLower().Contains("load"))
                {
                    string ps = "";
                    foreach (var p in m.GetParameters()) ps += (ps.Length > 0 ? ", " : "") + p.ParameterType.Name + " " + p.Name;
                    Debug.Log("[KkRenderBridge]   " + m.ReturnType.Name + " " + m.Name + "(" + ps + ")");
                }
        }
    }
}
