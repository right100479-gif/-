using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Globalization;
using System.Windows.Forms;
using ScriptPortal.Vegas;

public class EntryPoint
{
    private readonly string[] SectionNames = new string[] {
        "Verse 1",
        "Verse 2",
        "Chorus 1",
        "Verse 3",
        "Chorus 2",
        "Bridge",
        "Final Chorus 1",
        "Final Chorus 2",
        "Outro"
    };

    public void FromVegas(Vegas vegas)
    {
        List<Marker> markers = new List<Marker>();

        foreach (Marker marker in vegas.Project.Markers)
            markers.Add(marker);

        markers.Sort(delegate(Marker a, Marker b) {
            return a.Position.Nanos.CompareTo(b.Position.Nanos);
        });

        if (markers.Count != SectionNames.Length)
        {
            MessageBox.Show(
                "현재 프로젝트 마커가 " + markers.Count.ToString() + "개 있습니다.\n\n" +
                "이 곡에는 섹션 시작 마커가 정확히 " + SectionNames.Length.ToString() + "개 필요합니다.\n\n" +
                "순서:\n" +
                "1. Verse 1\n2. Verse 2\n3. Chorus 1\n4. Verse 3\n5. Chorus 2\n" +
                "6. Bridge\n7. Final Chorus 1\n8. Final Chorus 2\n9. Outro\n\n" +
                "각 구간의 첫 가사가 실제로 시작되는 지점에 마커를 찍은 뒤 다시 실행해 주세요.",
                "Worship Lyrics Auto 4.2",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information
            );
            return;
        }

        StringBuilder preview = new StringBuilder();
        preview.AppendLine("다음 9개 마커를 섹션 시작점으로 저장합니다.");
        preview.AppendLine();

        for (int i = 0; i < markers.Count; i++)
        {
            double seconds = markers[i].Position.Nanos / 10000000.0;
            preview.AppendLine(
                (i + 1).ToString("00") + ". " +
                SectionNames[i] + "  " +
                seconds.ToString("0.00", CultureInfo.InvariantCulture) + "초"
            );
        }

        preview.AppendLine();
        preview.Append("이 순서가 맞습니까?");

        if (MessageBox.Show(
            preview.ToString(),
            "Worship Lyrics Auto 4.2",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question
        ) != DialogResult.Yes)
            return;

        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string dataDir = Path.Combine(local, "WorshipLyricsAuto4", "data");
        Directory.CreateDirectory(dataDir);

        string output = Path.Combine(dataDir, "section_anchors.json");
        StringBuilder json = new StringBuilder();

        json.AppendLine("{");
        json.AppendLine("  \"version\": \"4.2\",");
        json.AppendLine("  \"anchors\": [");

        for (int i = 0; i < markers.Count; i++)
        {
            double seconds = markers[i].Position.Nanos / 10000000.0;
            json.Append("    {\"index\": ");
            json.Append((i + 1).ToString(CultureInfo.InvariantCulture));
            json.Append(", \"name\": \"");
            json.Append(SectionNames[i]);
            json.Append("\", \"seconds\": ");
            json.Append(seconds.ToString("0.000", CultureInfo.InvariantCulture));
            json.Append("}");
            if (i < markers.Count - 1) json.Append(",");
            json.AppendLine();
        }

        json.AppendLine("  ]");
        json.AppendLine("}");

        File.WriteAllText(output, json.ToString(), new UTF8Encoding(true));

        MessageBox.Show(
            "섹션 앵커 9개를 저장했습니다.\n\n" +
            output + "\n\n" +
            "이제 Worship Lyrics Auto 4.2에서 같은 곡을 다시 생성하세요.",
            "Worship Lyrics Auto 4.2",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        );
    }
}
